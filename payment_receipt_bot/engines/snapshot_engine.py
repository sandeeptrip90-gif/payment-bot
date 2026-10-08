"""
Playwright-based HTML to Image Snapshot Engine
"""
import random
from pathlib import Path
from typing import Any, Mapping, Optional

from playwright.async_api import async_playwright

from payment_receipt_bot.config import (
    MOBILE_PLAYWRIGHT_DEVICES,
    MOBILE_SCREENSHOT_VIEWPORT,
    MOBILE_VIEWPORTS,
    RECEIPT_OVERLAY_IMAGE,
)


class SnapshotEngine:
    """Captures mobile-sized screenshots of HTML files (single phone screen)."""

    def __init__(self, output_dir: str = "snapshots"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.playwright: Any = None
        self.browser: Any = None
        self.context: Any = None
        self.page: Any = None
        self._active_viewport: dict[str, int] = dict(MOBILE_SCREENSHOT_VIEWPORT)

    def _device_options(self) -> dict[str, Any]:
        if self.playwright:
            pool = [n for n in MOBILE_PLAYWRIGHT_DEVICES if n in self.playwright.devices]
            if pool:
                return dict(self.playwright.devices[random.choice(pool)])
        return {
            "viewport": dict(random.choice(MOBILE_VIEWPORTS)),
            "device_scale_factor": 2,
            "is_mobile": True,
            "has_touch": True,
        }

    async def _ensure_mobile_context(self) -> None:
        """New browser context emulating a random phone (iPhone / Samsung / etc.)."""
        if self.context:
            await self.context.close()
            self.context = None
            self.page = None

        opts = self._device_options()
        viewport = opts.get("viewport") or MOBILE_SCREENSHOT_VIEWPORT
        self._active_viewport = dict(viewport)

        self.context = await self.browser.new_context(
            viewport=self._active_viewport,
            device_scale_factor=opts.get("device_scale_factor", 2),
            is_mobile=opts.get("is_mobile", True),
            has_touch=opts.get("has_touch", True),
            user_agent=opts.get("user_agent"),
        )
        self.page = await self.context.new_page()

    async def initialize(self):
        """Initialize Playwright browser."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-accelerated-2d-canvas",
                "--disable-gpu",
                "--allow-file-access-from-files",
            ],
        )
        await self._ensure_mobile_context()

    async def _inject_receipt_stamp(self) -> None:
        """Small brand stamp near UTR / transaction id; random tilt and offset each capture."""
        if not self.page or not RECEIPT_OVERLAY_IMAGE.is_file():
            return
        src = RECEIPT_OVERLAY_IMAGE.resolve().as_uri()
        rot = random.uniform(-22, 22)
        size = random.randint(100, 140)
        jitter_x = random.randint(-14, 14)
        jitter_y = random.randint(-12, 12)
        await self.page.evaluate(
            """(opts) => {
              const { src, rot, size, jitterX, jitterY } = opts;
              const node =
                document.querySelector('.utr') ||
                document.querySelector('.utr-line .utr');
              let anchorTop = window.innerHeight * 0.62;
              let anchorLeft = window.innerWidth * 0.5;
              if (node) {
                const r = node.getBoundingClientRect();
                if (r.width > 0 && r.height > 0) {
                  anchorTop = r.top + r.height / 2 + jitterY;
                  anchorLeft = r.left + r.width / 2 + jitterX;
                }
              }
              const wrap = document.createElement('div');
              wrap.id = 'receipt-stamp-overlay';
              wrap.style.cssText = [
                'position:fixed',
                'top:' + anchorTop + 'px',
                'left:' + anchorLeft + 'px',
                'width:0',
                'height:0',
                'margin:0',
                'padding:0',
                'border:0',
                'overflow:visible',
                'z-index:2147483647',
                'pointer-events:none',
                'isolation:isolate',
              ].join(';');
              const img = document.createElement('img');
              img.src = src;
              img.alt = '';
              img.style.cssText = [
                'position:absolute',
                'top:' + (-size / 2) + 'px',
                'left:' + (-size / 2) + 'px',
                'width:' + size + 'px',
                'height:auto',
                'max-width:' + size + 'px',
                'display:block',
                'margin:0',
                'padding:0',
                'border:0',
                'transform:rotate(' + rot + 'deg)',
                'transform-origin:center center',
                'opacity:1',
              ].join(';');
              wrap.appendChild(img);
              document.body.appendChild(wrap);
            }""",
            {
                "src": src,
                "rot": rot,
                "size": size,
                "jitterX": jitter_x,
                "jitterY": jitter_y,
            },
        )
        try:
            await self.page.wait_for_function(
                """() => {
                  const img = document.querySelector('#receipt-stamp-overlay img');
                  return img && img.complete && img.naturalWidth > 0;
                }""",
                timeout=5000,
            )
        except Exception:
            await self.page.wait_for_timeout(200)

    async def capture(
        self,
        html_file: Path,
        output_name: Optional[str] = None,
        *,
        viewport: Optional[Mapping[str, int]] = None,
        full_page: bool = False,
        selector: Optional[str] = None,
    ) -> Path:
        """
        Capture one phone-screen PNG (viewport only, not full scrollable page).
        """
        if not self.browser:
            await self.initialize()
        elif viewport is not None:
            if not self.page:
                await self._ensure_mobile_context()
            await self.page.set_viewport_size(dict(viewport))
            self._active_viewport = dict(viewport)
        else:
            await self._ensure_mobile_context()

        file_url = html_file.resolve().as_uri()
        await self.page.goto(file_url, wait_until="load")
        try:
            await self.page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            await self.page.wait_for_timeout(500)

        await self._inject_receipt_stamp()

        if output_name is None:
            output_name = html_file.stem

        output_path = self.output_dir / f"{output_name}.png"

        if selector:
            target = self.page.locator(selector).first
            await target.wait_for(state="visible", timeout=5000)
            await target.screenshot(path=str(output_path), type="png")
        else:
            await self.page.screenshot(
                path=str(output_path),
                full_page=full_page,
                type="png",
            )

        return output_path

    async def capture_batch(self, html_files: list[Path]) -> list[dict[str, Any]]:
        """Capture screenshots for multiple HTML files."""
        results = []
        for html_file in html_files:
            try:
                output_path = await self.capture(html_file)
                results.append({
                    "html_file": html_file,
                    "screenshot_path": output_path,
                    "success": True,
                })
            except Exception as e:
                results.append({
                    "html_file": html_file,
                    "error": str(e),
                    "success": False,
                })
        return results

    async def close(self):
        """Close browser."""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
        finally:
            if self.playwright:
                await self.playwright.stop()
            self.page = None
            self.context = None
            self.browser = None
            self.playwright = None
