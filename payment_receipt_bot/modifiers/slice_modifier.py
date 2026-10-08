"""
Slice HTML Modifier — renders html_temp_all/slice/slice_payment.html.
"""
from pathlib import Path
from typing import Any, Dict

from payment_receipt_bot.config import SLICE_TEMPLATE

from .base_modifier import BaseModifier


class SliceModifier(BaseModifier):
    app_name = "slice"
    data_style = "slice"

    def __init__(self, html_template: Path):
        template = SLICE_TEMPLATE if SLICE_TEMPLATE.is_file() else Path(html_template)
        super().__init__(template)

    def _set_class_text(self, class_name: str, text: str) -> None:
        if self.soup is None:
            return
        node = self.soup.select_one(f".{class_name}")
        if node is None:
            print(f"[warn] SliceModifier: .{class_name} not found")
            return
        node.string = str(text)

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

    def modify(self, data: Dict[str, Any]) -> str:
        self.reset()
        amount = int(data["amount"])
        self._set_class_text("amount", f"₹{amount:,}")
        self._set_class_text("receiver_name", f"To {data['receiver_name']}")
        self._set_class_text("receiver_upi", data["receiver_upi"])
        self._set_class_text("datetime_formatted", data["datetime_formatted"])
        self._set_class_text("payer_name", "From slice savings")
        payer_tail = str(data.get("payer_account", "") or data.get("payer_upi", ""))
        digits = "".join(ch for ch in payer_tail if ch.isdigit())
        masked = f"xx{digits[-4:]}" if len(digits) >= 4 else payer_tail
        self._set_class_text("payer_upi", masked)
        rrn = data.get("rrn") or data.get("utr")
        self._set_class_text("utr", f"RRN: {rrn}")
        self._fix_asset_urls()
        if self.soup is None:
            return ""
        return self.soup.decode(formatter="html")
