"""Unit tests for the Payment Receipt Bot."""
import os
import sys
import json
import shutil
import asyncio
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent
sys.path.insert(0, str(PARENT))

import payment_receipt_bot
from payment_receipt_bot import config as cfg_mod
from payment_receipt_bot.config import BotConfig, INDIAN_BANKS, REGIONAL_NAMES
from payment_receipt_bot.engines.data_generator import IndianDataGenerator
from payment_receipt_bot.engines.snapshot_engine import SnapshotEngine
from payment_receipt_bot.utils.image_processor import compress_image, get_image_size
from payment_receipt_bot.utils.validators import validate_amount, validate_app
from payment_receipt_bot.modifiers import MODIFIERS
from payment_receipt_bot.modifiers.base_modifier import BaseModifier

config = cfg_mod
TEMPLATES_DIR = cfg_mod.TEMPLATES_DIR
DATA_DIR = cfg_mod.DATA_DIR
OUTPUT_DIR = cfg_mod.OUTPUT_DIR

passed = 0
failed = 0


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        print(f"  PASS  {name}")
        passed += 1
    else:
        print(f"  FAIL  {name} {detail}")
        failed += 1


# --- config tests ---
print("\n[config]")
with tempfile.TemporaryDirectory() as tmp:
    cfg_file = Path(tmp) / "bot_config.json"
    cfg = BotConfig(str(cfg_file))
    check("default telegram_token empty", cfg.get("telegram_token") == "")
    check("default admin_user_id 0", cfg.get("admin_user_id") == 0)
    check("default mode batch", cfg.get("sending_mode") == "batch")
    check("default delay 4", cfg.get("delay_between_receipts") == 4)
    check("default amount_min 1000", cfg.get("amount_min") == 1000)
    check("default amount_max 50000", cfg.get("amount_max") == 50000)
    check("default realism 3", cfg.get("data_realism_level") == 3)

    cfg.set("telegram_token", "test_token_123")
    cfg.update_batch(amount_min=5000, amount_max=25000)
    cfg2 = BotConfig(str(cfg_file))
    check("persisted telegram_token", cfg2.get("telegram_token") == "test_token_123")
    check("persisted amount_min", cfg2.get("amount_min") == 5000)
    check("persisted amount_max", cfg2.get("amount_max") == 25000)

check("data dir exists", config.DATA_DIR.exists())
check("templates dir exists", config.TEMPLATES_DIR.exists())
check("output dir exists", config.OUTPUT_DIR.exists())

check("INDIAN_BANKS >= 20", len(INDIAN_BANKS) >= 20)
for name, b in INDIAN_BANKS.items():
    for key in ("code", "utr_prefix", "upi_handles", "ifsc_prefix"):
        if key not in b:
            check(f"bank {name} has {key}", False, f"missing {key}")
    if len(b.get("utr_prefix", [])) < 1:
        check(f"bank {name} utr_prefix not empty", False)
    if len(b.get("upi_handles", [])) < 1:
        check(f"bank {name} upi_handles not empty", False)

check("REGIONAL_NAMES has 4 regions", len(REGIONAL_NAMES) == 4)
for region, data in REGIONAL_NAMES.items():
    for key in ("states", "surnames", "first_names_male", "first_names_female"):
        if key not in data:
            check(f"region {region} has {key}", False, f"missing {key}")
    if len(data.get("surnames", [])) < 5:
        check(f"region {region} surnames >=5", False)
    if len(data.get("first_names_male", [])) < 5:
        check(f"region {region} male names >=5", False)
    if len(data.get("first_names_female", [])) < 5:
        check(f"region {region} female names >=5", False)

# --- data generator tests ---
print("\n[data_generator]")
gen = IndianDataGenerator(realism_level=3)
for _ in range(50):
    name = gen.generate_indian_name()
    if len(name.split()) < 2:
        check("name has >=2 parts", False, name)
        break
else:
    check("name has >=2 parts (50 samples)", True)

for _ in range(20):
    n = gen.generate_indian_name(gender="male")
    if not n.split()[0].isalpha():
        check("male name alpha", False, n)
        break
else:
    check("male names valid (20 samples)", True)

for region in ("North", "South", "West", "East"):
    n = gen.generate_indian_name(region=region)
    if not n:
        check(f"name for {region}", False)
        break
else:
    check("names for all regions", True)

bank_name, bank_details = gen.generate_bank()
check("generated bank in INDIAN_BANKS", bank_name in INDIAN_BANKS)
check("bank_details has code", "code" in bank_details)

upi = gen.generate_upi_id("Rajesh Kumar", "State Bank of India")
check("UPI has @", "@" in upi)
check("UPI ends with SBI handle", upi.endswith("@oksbi") or upi.endswith("@sbi"))

utr = gen.generate_utr("State Bank of India")
check("UTR SBI length 12", len(utr) == 12)
check("UTR SBI prefix digit", utr[0] in ("3", "4"))

utr_hdfc = gen.generate_utr("HDFC Bank")
check("UTR HDFC prefix 5", utr_hdfc[0] == "5")

ifsc = gen.generate_ifsc("State Bank of India")
check("IFSC length 11", len(ifsc) == 11)
check("IFSC starts SBIN", ifsc.startswith("SBIN"))

ifsc_hdfc = gen.generate_ifsc("HDFC Bank")
check("HDFC IFSC starts HDFC", ifsc_hdfc.startswith("HDFC"))

amount = gen.generate_amount(1000, 50000, "thousands")
check("amount thousands >= min", amount >= 1000)
check("amount thousands <= max", amount <= 50000)
check("amount multiple of 1000", amount % 1000 == 0)

amount_any = gen.generate_amount(1000, 50000, "any")
check("amount any multiple of 100", amount_any % 100 == 0)

dt = gen.generate_datetime()
check("datetime is datetime", isinstance(dt, datetime))
check("datetime <= now", dt <= datetime.now())

formatted = gen.format_datetime_indian(dt, "gpay")
check("formatted has year 202x", "202" in formatted)
check("formatted has colon", ":" in formatted)

txn = gen.generate_complete_transaction({
    "receiver_mode": "random",
    "payer_mode": "random",
    "amount_min": 1000,
    "amount_max": 50000,
    "amount_rounding": "thousands",
    "utr_mode": "random",
    "datetime_mode": "random",
}, app="gpay")
for key in ("receiver_name", "payer_name", "amount", "utr", "datetime",
            "datetime_formatted", "receiver_bank", "payer_bank",
            "receiver_upi", "payer_upi", "receiver_account", "payer_account"):
    if key not in txn:
        check(f"txn has {key}", False)
        break
else:
    check("txn has all expected keys", True)
check("txn amount in range", 1000 <= txn["amount"] <= 50000)
check("txn utr length 12", len(txn["utr"]) == 12)

# --- snapshot engine tests ---
print("\n[snapshot_engine]")

async def snapshot_test():
    engine = SnapshotEngine(output_dir=str(ROOT / "snapshots" / "test_unit"))
    try:
        await engine.initialize()
        check("browser initialized", engine.browser is not None)
        check("page created", engine.page is not None)

        # build a small html
        test_html = ROOT / "snapshots" / "test_unit_input.html"
        test_html.parent.mkdir(parents=True, exist_ok=True)
        test_html.write_text(
            "<html><body style='background:#fff;padding:30px;'><h1>HELLO</h1></body></html>",
            encoding="utf-8",
        )
        out = await engine.capture(test_html, "unit_test")
        check("screenshot file exists", out.exists())
        check("screenshot has size", out.stat().st_size > 0)
        check("screenshot is PNG", out.suffix.lower() == ".png")
        test_html.unlink(missing_ok=True)
    finally:
        await engine.close()

asyncio.run(snapshot_test())

# --- modifier tests ---
print("\n[modifiers]")
for app_key, modifier_cls in MODIFIERS.items():
    fname = f"{app_key}_payment.html"
    if app_key == "navi":
        fname = "navi_upi_payment.html"
    if app_key == "supermoney":
        fname = "supermoney_payment.html"
    if app_key == "payzapp":
        fname = "payzapp_payment.html"
    html_file = ROOT / "html_templates" / fname
    if not html_file.exists():
        check(f"template exists for {app_key}", False, str(html_file))
        continue
    check(f"template exists for {app_key}", True)
    m = modifier_cls(html_file)
    test_data = {
        "receiver_name": "Rajesh Kumar",
        "payer_name": "Amit Sharma",
        "amount": 5000,
        "datetime": datetime.now(),
        "datetime_formatted": "29 Apr 2026, 03:27 PM",
        "receiver_bank": "State Bank of India",
        "payer_bank": "HDFC Bank",
        "receiver_account": "XXXXXX1234",
        "payer_account": "XXXXXX5678",
        "receiver_upi": "rajeshkumar123@oksbi",
        "payer_upi": "amitsharma456@okhdfcbank",
        "utr": "312345678901",
    }
    rendered = m.modify(test_data)
    check(f"{app_key}: receiver in output", test_data["receiver_name"] in rendered)
    check(f"{app_key}: no $placeholder remaining", "$" not in rendered or "$(" in rendered)
    check(f"{app_key}: amount formatted 5,000", "5,000" in rendered)
    check(f"{app_key}: utr present", test_data["utr"] in rendered)

# --- image processor ---
print("\n[image_processor]")
from PIL import Image
with tempfile.TemporaryDirectory() as tmp:
    src = Path(tmp) / "test.png"
    img = Image.new("RGB", (2000, 2000), color="red")
    img.save(src)
    out = compress_image(src, quality=85)
    check("compressed file exists", out.exists())
    check("compressed file non-empty", out.stat().st_size > 0)
    check("size getter works", get_image_size(out) == out.stat().st_size)
    out.unlink()

# --- validators ---
print("\n[validators]")
try:
    check("validate_amount(1000)", validate_amount(1000) == "1,000.00")
    check("validate_amount('2500.5')", validate_amount("2500.5") == "2,500.50")
except Exception as e:
    check("validate_amount works", False, str(e))
try:
    validate_amount(0)
    check("validate_amount rejects 0", False)
except ValueError:
    check("validate_amount rejects 0", True)
try:
    validate_amount(-1)
    check("validate_amount rejects -1", False)
except ValueError:
    check("validate_amount rejects -1", True)
try:
    check("validate_app normalizes", validate_app("GPay", ("gpay", "phonepe")) == "gpay")
except Exception as e:
    check("validate_app works", False, str(e))
try:
    validate_app("foo", ("gpay", "phonepe"))
    check("validate_app rejects unknown", False)
except ValueError:
    check("validate_app rejects unknown", True)

print(f"\n=== {passed} passed, {failed} failed ===")
sys.exit(0 if failed == 0 else 1)
