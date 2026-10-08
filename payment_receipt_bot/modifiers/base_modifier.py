"""
Base HTML Modifier - All modifiers inherit from this.

The provided HTML templates use simple `$placeholder` tokens
(e.g. $recipient, $amount, $date). Subclasses describe which
placeholders they want replaced via the ``placeholders`` mapping
returned by :meth:`build_placeholders`.
"""
import re
from pathlib import Path
from typing import Any, Dict

from bs4 import BeautifulSoup


_PLACEHOLDER_RE = re.compile(r"\$([a-zA-Z_][a-zA-Z0-9_]*)")


class BaseModifier:
    """Base class for all HTML modifiers."""

    app_name: str = "Payment"

    def __init__(self, html_template: Path):
        self.html_template = Path(html_template)
        self.html_source: str = ""
        self.soup: BeautifulSoup | None = None
        self.load_template()

    def load_template(self) -> None:
        with open(self.html_template, "r", encoding="utf-8") as f:
            self.html_source = f.read()
        self.soup = BeautifulSoup(self.html_source, "lxml")

    def reset(self) -> None:
        self.load_template()

    def build_placeholders(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Return the placeholder -> value mapping for this modifier.

        Subclasses should override this.
        """
        return {}

    def modify(self, data: Dict[str, Any]) -> str:
        placeholders = {"app_name": self.app_name, **self.build_placeholders(data)}

        rendered = self.html_source

        for key, value in placeholders.items():
            rendered = rendered.replace(f"${key}", str(value))

        missing = sorted(set(_PLACEHOLDER_RE.findall(rendered)) - set(placeholders.keys()))
        for token in missing:
            print(f"[warn] {self.__class__.__name__}: missing placeholder ${token}")
            rendered = rendered.replace(f"${token}", "")

        return rendered

    def save_modified(self, output_path: Path) -> Path:
        output_path = Path(output_path)
        rendered = self.modify({})
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(rendered)
        return output_path

    def get_text(self, selector: str) -> str:
        if self.soup is None:
            return ""
        element = self.soup.select_one(selector)
        return element.get_text().strip() if element else ""

    def set_text(self, selector: str, text: str) -> None:
        if self.soup is None:
            return
        element = self.soup.select_one(selector)
        if element:
            element.string = text
        else:
            print(f"[warn] {self.__class__.__name__}: selector not found: {selector}")
