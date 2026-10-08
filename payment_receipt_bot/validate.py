"""Final production-readiness validation."""
import os
import sys
import json
import warnings
warnings.filterwarnings("ignore")

from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))

errors = []
warnings_list = []

if sys.version_info < (3, 8):
    errors.append("Python 3.8+ required")

for mod in ("telegram", "playwright", "bs4", "PIL", "aiofiles", "pydantic",
            "dateutil", "faker", "lxml"):
    try:
        __import__(mod)
    except ImportError as e:
        errors.append(f"Missing dependency: {e}")

required = ["bot.py", "config.py", "requirements.txt"]
for f in required:
    if not (ROOT / f).exists():
        errors.append(f"Missing file: {f}")

# setup.py is at the project root, not inside the package
if not (ROOT.parent / "setup.py").exists():
    warnings_list.append("setup.py missing at project root")

for d in ("data", "html_templates", "modifiers", "engines", "utils"):
    if not (ROOT / d).is_dir():
        errors.append(f"Missing directory: {d}")

html_files = list((ROOT / "html_templates").glob("*.html"))
if not html_files:
    errors.append("No HTML templates found")
elif len(html_files) < 6:
    warnings_list.append(f"Only {len(html_files)} HTML templates")

cfg_path = ROOT / "bot_config.json"
if cfg_path.exists():
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    if not cfg.get("telegram_token"):
        warnings_list.append("telegram_token not set in bot_config.json")
    if not cfg.get("admin_user_id"):
        warnings_list.append("admin_user_id not set in bot_config.json")
else:
    warnings_list.append(
        "bot_config.json not found (run: python payment_receipt_bot\\setup_config.py)"
    )

# verify modifiers load
try:
    from payment_receipt_bot.modifiers import MODIFIERS
    expected = {"gpay", "phonepe", "slice", "supermoney", "payzapp", "navi"}
    missing = expected - set(MODIFIERS.keys())
    if missing:
        errors.append(f"Modifiers missing: {missing}")
except Exception as e:
    errors.append(f"Modifier import error: {e}")

# Playwright smoke test
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        b.close()
except Exception as e:
    errors.append(f"Playwright browser error: {e}")

print("=" * 60)
print("PRODUCTION READINESS REPORT")
print("=" * 60)
if errors:
    print(f"\nERRORS ({len(errors)}):")
    for e in errors:
        print(f"  - {e}")
if warnings_list:
    print(f"\nWARNINGS ({len(warnings_list)}):")
    for w in warnings_list:
        print(f"  - {w}")
if not errors and not warnings_list:
    print("\nALL CHECKS PASSED - READY FOR PRODUCTION")
elif not errors:
    print(f"\n{len(warnings_list)} warnings - review before production")
else:
    print(f"\n{len(errors)} errors - fix before production")
print("=" * 60)
sys.exit(0 if not errors else 1)
