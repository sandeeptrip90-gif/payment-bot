"""
Indian Data Generator - Creates realistic Indian financial data.
"""
import random
import string
from datetime import datetime, timedelta
from typing import Tuple, Dict, Any
from zoneinfo import ZoneInfo

from ..config import INDIAN_BANKS, REGIONAL_NAMES


class IndianDataGenerator:
    """Generates realistic Indian banking and personal data."""

    def __init__(self, realism_level: int = 3):
        self.realism_level = realism_level
        self.banks = list(INDIAN_BANKS.keys())

    def generate_indian_name(self, gender: str = None, region: str = None) -> str:
        if gender is None:
            gender = random.choice(["male", "female"])
        if region is None:
            region = random.choice(list(REGIONAL_NAMES.keys()))

        region_data = REGIONAL_NAMES[region]
        if gender == "male":
            first_name = random.choice(region_data["first_names_male"])
        else:
            first_name = random.choice(region_data["first_names_female"])
        surname = random.choice(region_data["surnames"])

        if random.random() > 0.6:
            middle_initial = random.choice(string.ascii_uppercase)
            return f"{first_name} {middle_initial} {surname}"
        return f"{first_name} {surname}"

    def generate_bank(self, preferred_bank: str = None) -> Tuple[str, Dict]:
        if preferred_bank and preferred_bank in INDIAN_BANKS:
            bank_name = preferred_bank
        else:
            bank_name = random.choice(self.banks)
        return bank_name, INDIAN_BANKS[bank_name]

    def generate_upi_id(self, name: str, bank_name: str = None) -> str:
        if bank_name:
            bank_details = INDIAN_BANKS.get(bank_name)
        else:
            _, bank_details = self.generate_bank()

        name_part = "".join(name.lower().split()).replace(".", "")
        name_part += str(random.randint(100, 9999))
        upi_handle = random.choice(bank_details["upi_handles"])
        return f"{name_part}{upi_handle}"

    def generate_utr(self, bank_name: str, length: int = 12) -> str:
        bank_details = INDIAN_BANKS.get(bank_name)
        if not bank_details:
            return "".join(random.choices(string.digits, k=length))
        prefix = random.choice(bank_details["utr_prefix"])
        remaining = length - len(prefix)
        return prefix + "".join(random.choices(string.digits, k=remaining))

    def generate_ifsc(self, bank_name: str) -> str:
        bank_details = INDIAN_BANKS.get(bank_name)
        if not bank_details:
            return "XXXX0" + "".join(random.choices(string.digits, k=5))
        prefix = bank_details["ifsc_prefix"]
        remaining = 11 - len(prefix)
        return prefix + "0" + "".join(random.choices(string.digits, k=remaining - 1))

    def generate_amount(self, min_amount: int = 1000, max_amount: int = 50000,
                        rounding: str = "thousands") -> int:
        min_amount = int(min_amount)
        max_amount = int(max_amount)
        if min_amount > max_amount:
            min_amount, max_amount = max_amount, min_amount
        step = 1000 if rounding == "thousands" else 100
        first = ((min_amount + step - 1) // step) * step
        last = (max_amount // step) * step
        if first > last:
            return min(max_amount, max(min_amount, (min_amount + max_amount) // 2))
        choices = (last - first) // step + 1
        return first + random.randint(0, choices - 1) * step

    def generate_datetime(self, custom_datetime: str = None) -> datetime:
        if custom_datetime:
            try:
                return datetime.fromisoformat(custom_datetime)
            except ValueError:
                pass
        now_ist = datetime.now(ZoneInfo("Asia/Kolkata"))
        min_ago = timedelta(minutes=5)
        max_ago = timedelta(hours=3)
        window_seconds = int((max_ago - min_ago).total_seconds())
        return now_ist - max_ago + timedelta(seconds=random.randint(0, window_seconds))

    def format_datetime_indian(self, dt: datetime = None, style: str = "gpay") -> str:
        if dt is None:
            dt = self.generate_datetime()
        formats = {
            "gpay": "%d %b %Y, %I:%M %p",
            "gpay_dark": "%B %d, %Y %I:%M %p",
            "phonepe": "%d %B %Y at %I:%M %p",
            "slice": "%d %b '%y, %I:%M %p",
            "supermoney": "%b %d at %I:%M %p",
            "payzapp": "%d %B %Y, %I:%M %p",
            "navi": "%d %b %Y, %I:%M %p",
        }
        fmt = formats.get(style, formats["gpay"])
        return dt.strftime(fmt)

    def generate_complete_transaction(self, config: Dict[str, Any], app: str = "gpay") -> Dict[str, Any]:
        data: Dict[str, Any] = {}

        if config.get("receiver_mode") == "custom" and config.get("custom_receiver_name"):
            receiver_name = config["custom_receiver_name"]
        else:
            receiver_name = self.generate_indian_name()
        data["receiver_name"] = receiver_name

        if config.get("payer_mode") == "custom" and config.get("custom_payer_name"):
            payer_name = config["custom_payer_name"]
        else:
            payer_name = self.generate_indian_name()
        data["payer_name"] = payer_name

        receiver_bank, _ = self.generate_bank()
        payer_bank, _ = self.generate_bank()
        data["receiver_bank"] = receiver_bank
        data["payer_bank"] = payer_bank

        if config.get("receiver_upi_mode") == "custom" and config.get("custom_receiver_upi"):
            data["receiver_upi"] = str(config["custom_receiver_upi"]).strip()
        else:
            data["receiver_upi"] = self.generate_upi_id(receiver_name, receiver_bank)
        data["payer_upi"] = self.generate_upi_id(payer_name, payer_bank)

        custom_amount = config.get("custom_amount")
        if custom_amount is not None and str(custom_amount).strip() != "":
            amount = int(custom_amount)
        else:
            amount = self.generate_amount(
                int(config.get("amount_min", 1000)),
                int(config.get("amount_max", 50000)),
                config.get("amount_rounding", "thousands"),
            )
        data["amount"] = amount

        if config.get("utr_mode") == "custom" and config.get("custom_utr"):
            utr = str(config["custom_utr"]).zfill(12)[:12]
        else:
            utr = self.generate_utr(receiver_bank)
        data["utr"] = utr
        data["rrn"] = self.generate_utr(receiver_bank, length=12)

        if config.get("datetime_mode") == "custom" and config.get("custom_datetime"):
            dt = self.generate_datetime(config["custom_datetime"])
        else:
            dt = self.generate_datetime()

        data["datetime"] = dt
        data["datetime_formatted"] = self.format_datetime_indian(dt, app)

        data["receiver_ifsc"] = self.generate_ifsc(receiver_bank)
        data["payer_ifsc"] = self.generate_ifsc(payer_bank)

        data["receiver_account"] = "XXXXXX" + str(random.randint(1000, 9999))
        data["payer_account"] = "XXXXXX" + str(random.randint(1000, 9999))

        return data
