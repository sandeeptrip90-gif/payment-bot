"""
Google Pay HTML Modifier — gpay_dark.html and gpay_light.html (by trigger filename).
"""
import random
import secrets
import string
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.parse import quote

from payment_receipt_bot.config import GPAY_DARK_TEMPLATE, GPAY_LIGHT_TEMPLATE

from .base_modifier import BaseModifier

# Logos in html_temp_all/Bank logo — clip is (object-x%, object-y%, zoom).
_LIGHT_BANK_LOGOS: Tuple[Dict[str, Any], ...] = (
    {"name": "Axis Bank", "hints": ("axis",), "clip": (50, 36, 1.85)},
    {"name": "Canara Bank", "hints": ("canara",), "clip": (10, 50, 2.55)},
    {"name": "Punjab National Bank", "hints": ("punjab", "pnb"), "clip": (30, 50, 2.05)},
    {"name": "Indian Overseas Bank", "hints": ("overseas", "pinimg", "google image"), "clip": (50, 35, 2.15)},
    {"name": "ICICI Bank", "hints": ("icici",), "clip": (50, 50, 1.50)},
    {"name": "State Bank of India", "hints": ("sbi",), "clip": (50, 50, 1.22)},
    {"name": "UCO Bank", "hints": ("uco",), "clip": (50, 48, 1.95)},
)


class GPayModifier(BaseModifier):
    app_name = "Google Pay"
    data_style = "gpay_dark"

    def __init__(self, html_template: Path):
        trigger = Path(html_template)
        stem = trigger.stem.lower()
        self._is_light = "light" in stem
        if self._is_light:
            template = GPAY_LIGHT_TEMPLATE if GPAY_LIGHT_TEMPLATE.is_file() else trigger
        else:
            template = GPAY_DARK_TEMPLATE if GPAY_DARK_TEMPLATE.is_file() else trigger
        super().__init__(template)

    def _set_class_text(self, class_name: str, text: str) -> None:
        if self.soup is None:
            return
        node = self.soup.select_one(f".{class_name}")
        if node is None:
            print(f"[warn] GPayModifier: .{class_name} not found")
            return
        node.string = str(text)

    def _avatar_seed(self, name: str) -> str:
        parts = [p for p in str(name).strip().split() if p]
        if not parts:
            return "U"
        if len(parts) == 1:
            return parts[0][:2].upper()
        return (parts[0][0] + parts[-1][0]).upper()

    def _set_avatar(self, name: str) -> None:
        if self.soup is None:
            return
        img = self.soup.select_one(".avatar_img, .avatar img")
        if img is None:
            return
        safe_name = str(name).strip() or "User"
        seed = self._avatar_seed(safe_name)
        img["src"] = (
            "https://api.dicebear.com/10.x/initials/svg"
            f"?seed={quote(seed)}"
            "&backgroundColor=8526b5&radius=50"
        )
        img["alt"] = seed
        img["width"] = "96"
        img["height"] = "96"

    def _fix_asset_urls(self) -> None:
        if self.soup is None:
            return
        base = self.html_template.parent.resolve()
        for img in self.soup.select("img[src]"):
            src = img.get("src", "")
            if not src or src.startswith(("http://", "https://", "data:", "file:")):
                continue
            path = (base / src).resolve()
            if path.is_file():
                img["src"] = path.as_uri()

    def _bank_logo_dir(self) -> Path:
        return (self.html_template.parent.parent / "Bank logo").resolve()

    def _find_logo_file(self, hints: Tuple[str, ...]) -> Optional[Path]:
        folder = self._bank_logo_dir()
        if not folder.is_dir():
            return None
        files = [f for f in folder.iterdir() if f.is_file()]
        for hint in hints:
            needle = hint.lower()
            for path in files:
                if needle in path.name.lower():
                    return path
        return None

    def _pick_light_bank(self) -> Optional[Dict[str, Any]]:
        available = []
        for bank in _LIGHT_BANK_LOGOS:
            path = self._find_logo_file(tuple(bank["hints"]))
            if path is not None:
                available.append({**bank, "path": path})
        if not available:
            return None
        return random.choice(available)

    def _generate_google_txn_id(self) -> str:
        alphabet = string.ascii_letters + string.digits
        return "CI" + "".join(secrets.choice(alphabet) for _ in range(10))

    def _apply_bank_clip(self, img, clip: Tuple[float, float, float]) -> None:
        x, y, zoom = clip
        px = min(100.0, max(0.0, x + random.uniform(-4.5, 4.5)))
        py = min(100.0, max(0.0, y + random.uniform(-4.5, 4.5)))
        scale = min(2.9, max(1.08, zoom + random.uniform(-0.10, 0.14)))
        img["style"] = (
            f"object-position:{px:.1f}% {py:.1f}%;"
            f"transform:scale({scale:.2f})"
        )

    def _set_light_bank(self, data: Dict[str, Any]) -> None:
        if self.soup is None:
            return
        bank = self._pick_light_bank()
        if bank is None:
            print("[warn] GPayModifier: no bank logos found")
            return
        name = bank["name"]
        logo = self.soup.select_one(".bank-logo")
        img = self.soup.select_one(".bank-logo img")
        if logo is not None:
            logo["aria-label"] = f"{name} logo"
        if img is not None:
            img["src"] = bank["path"].as_uri()
            img["alt"] = name
            self._apply_bank_clip(img, bank["clip"])
        self._set_class_text("receiver_bank", name)
        from_bank = self.soup.select_one(".from_bank")
        if from_bank is not None:
            from_bank.string = name
        acct = self.soup.select_one(".bank-acct")
        if acct is not None:
            raw = str(data.get("receiver_account") or "")
            digits = "".join(ch for ch in raw if ch.isdigit())
            last4 = digits[-4:] if len(digits) >= 4 else f"{random.randint(1000, 9999)}"
            acct.string = f"XXXXXXXXXX{last4}"

    def modify(self, data: Dict[str, Any]) -> str:
        self.reset()
        amount = int(data["amount"])
        amount_text = f"{amount:,}.00"

        if self._is_light:
            if self.soup and self.soup.select_one(".rupee"):
                self._set_class_text("amount", amount_text)
            else:
                self._set_class_text("amount", f"₹{amount_text}")
            self._set_class_text("receiver_name", data["receiver_name"])
            self._set_class_text("receiver_upi", data["receiver_upi"])
            self._set_class_text("datetime_formatted", data["datetime_formatted"])
            self._set_class_text("utr", data["utr"])
            self._set_class_text("google_txn_id", self._generate_google_txn_id())
            self._set_avatar(data["receiver_name"])
            self._set_light_bank(data)
            self._fix_asset_urls()
        else:
            self._set_class_text("amount", f"₹{amount_text}")
            self._set_class_text("receiver_name", data["receiver_name"])
            self._set_class_text("receiver_upi", data["receiver_upi"])
            self._set_class_text("datetime_formatted", data["datetime_formatted"])
            self._set_class_text("utr", data["utr"])

        if self.soup is None:
            return ""
        return self.soup.decode(formatter="html")
