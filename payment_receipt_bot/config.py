"""
Configuration management for Payment Receipt Bot
"""
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent


class BotConfig:
    """Bot configuration manager"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = Path(config_file) if config_file else BASE_DIR / "bot_config.json"
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        default_config = {
            "telegram_token": "",
            "admin_user_id": 0,
    "sending_mode": "batch",
            "delay_between_receipts": 4,
            "amount_min": 1000,
            "amount_max": 50000,
            "amount_rounding": "thousands",
            "receiver_mode": "random",
            "payer_mode": "random",
            "custom_receiver_name": "",
            "receiver_upi_mode": "random",
            "custom_receiver_upi": "",
            "custom_payer_name": "",
            "custom_amount": None,
            "utr_mode": "random",
            "custom_utr": "",
            "datetime_mode": "random",
            "custom_datetime": "",
            "data_realism_level": 3,
            "banks_to_include": "all",
            "last_modified": datetime.now().isoformat(),
        }

        if self.config_file.exists():
            try:
                with self.config_file.open('r', encoding='utf-8') as f:
                    saved_config = json.load(f)
                    # Merge with defaults
                    default_config.update(saved_config)
            except Exception as e:
                print(f"⚠️  Error loading config: {e}")
        
        return default_config
    
    def save_config(self):
        """Save configuration to file"""
        self.config["last_modified"] = datetime.now().isoformat()
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with self.config_file.open('w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
    
    def get(self, key: str, default=None):
        """Get configuration value"""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set configuration value"""
        self.config[key] = value
        self.save_config()
    
    def update_batch(self, **kwargs):
        """Update multiple config values at once"""
        for key, value in kwargs.items():
            self.config[key] = value
        self.save_config()


# Path configurations
DATA_DIR = BASE_DIR / "data"
TEMPLATES_DIR = BASE_DIR / "html_temp_all"
GPAY_DARK_TEMPLATE = BASE_DIR / "html_temp_all" / "google_pay" / "gpay_dark.html"
GPAY_LIGHT_TEMPLATE = BASE_DIR / "html_temp_all" / "google_pay" / "gpay_light.html"
SLICE_TEMPLATE = BASE_DIR / "html_temp_all" / "slice" / "slice_payment.html"
OUTPUT_DIR = BASE_DIR / "snapshots"
RECEIPT_OVERLAY_IMAGE = BASE_DIR / "assets" / "receipt_overlay.webp"

# One phone screen per screenshot (no full-page scroll). Sizes match common handsets.
MOBILE_SCREENSHOT_VIEWPORT = {"width": 412, "height": 915}
MOBILE_VIEWPORTS = (
    {"width": 390, "height": 844},   # iPhone 14 / 15 class
    {"width": 393, "height": 873},   # Redmi / many 6.5" Android phones
    {"width": 412, "height": 915},   # Samsung Galaxy / Pixel tall
    {"width": 412, "height": 892},   # Motorola / similar aspect
    {"width": 360, "height": 800},   # compact Android
)
# Playwright device presets (viewport + UA + touch); used when available
MOBILE_PLAYWRIGHT_DEVICES = (
    "iPhone 14",
    "iPhone 13",
    "Pixel 7",
    "Galaxy S24",
    "Galaxy S9+",
    "Moto G4",
)

# Ensure directories exist
OUTPUT_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

# Indian banks with UTR prefixes
INDIAN_BANKS = {
    "State Bank of India": {
        "code": "SBI",
        "utr_prefix": ["3", "4"],
        "upi_handles": ["@oksbi", "@sbi"],
        "ifsc_prefix": "SBIN"
    },
    "HDFC Bank": {
        "code": "HDFC",
        "utr_prefix": ["5"],
        "upi_handles": ["@okhdfcbank", "@hdfcbank"],
        "ifsc_prefix": "HDFC"
    },
    "ICICI Bank": {
        "code": "ICICI",
        "utr_prefix": ["6"],
        "upi_handles": ["@okicici", "@icici"],
        "ifsc_prefix": "ICIC"
    },
    "Axis Bank": {
        "code": "AXIS",
        "utr_prefix": ["7"],
        "upi_handles": ["@axl", "@axis"],
        "ifsc_prefix": "UTIB"
    },
    "Kotak Mahindra Bank": {
        "code": "KOTAK",
        "utr_prefix": ["8"],
        "upi_handles": ["@okaxis", "@kotak"],
        "ifsc_prefix": "KKBK"
    },
    "Bank of Baroda": {
        "code": "BOB",
        "utr_prefix": ["2"],
        "upi_handles": ["@barodampay", "@bob"],
        "ifsc_prefix": "BARB"
    },
    "Punjab National Bank": {
        "code": "PNB",
        "utr_prefix": ["1"],
        "upi_handles": ["@pnb", "@pnbpay"],
        "ifsc_prefix": "PUNB"
    },
    "Canara Bank": {
        "code": "CANARA",
        "utr_prefix": ["9"],
        "upi_handles": ["@canarabank", "@canara"],
        "ifsc_prefix": "CNRB"
    },
    "Union Bank of India": {
        "code": "UNION",
        "utr_prefix": ["0"],
        "upi_handles": ["@unionbank", "@ubi"],
        "ifsc_prefix": "UBIN"
    },
    "Indian Bank": {
        "code": "INDIAN",
        "utr_prefix": ["35", "36"],
        "upi_handles": ["@ibl", "@indianbank"],
        "ifsc_prefix": "IDIB"
    },
    "Yes Bank": {
        "code": "YES",
        "utr_prefix": ["55", "56"],
        "upi_handles": ["@ybl", "@yesbank"],
        "ifsc_prefix": "YESB"
    },
    "IDFC First Bank": {
        "code": "IDFC",
        "utr_prefix": ["65", "66"],
        "upi_handles": ["@idfcfirstbank", "@idfc"],
        "ifsc_prefix": "IDFB"
    },
    "Federal Bank": {
        "code": "FEDERAL",
        "utr_prefix": ["75", "76"],
        "upi_handles": ["@fedbank", "@federal"],
        "ifsc_prefix": "FDRL"
    },
    "RBL Bank": {
        "code": "RBL",
        "utr_prefix": ["85", "86"],
        "upi_handles": ["@rbl", "@rblbank"],
        "ifsc_prefix": "RATN"
    },
    "IndusInd Bank": {
        "code": "INDUSIND",
        "utr_prefix": ["95", "96"],
        "upi_handles": ["@indusind", "@indusindbank"],
        "ifsc_prefix": "INDB"
    },
    "Paytm Payments Bank": {
        "code": "PAYTM",
        "utr_prefix": ["11", "12"],
        "upi_handles": ["@paytm", "@ptys"],
        "ifsc_prefix": "PBYB"
    },
    "Airtel Payments Bank": {
        "code": "AIRTEL",
        "utr_prefix": ["13", "14"],
        "upi_handles": ["@airtel", "@airtelpb"],
        "ifsc_prefix": "APBL"
    },
    "Jio Payments Bank": {
        "code": "JIO",
        "utr_prefix": ["15", "16"],
        "upi_handles": ["@jiopay", "@jio"],
        "ifsc_prefix": "JIOP"
    },
    "Indian Overseas Bank": {
        "code": "IOB",
        "utr_prefix": ["17", "18"],
        "upi_handles": ["@iob", "@iobank"],
        "ifsc_prefix": "IOBA"
    },
    "Central Bank of India": {
        "code": "CENTRAL",
        "utr_prefix": ["19", "20"],
        "upi_handles": ["@centralbank", "@cbi"],
        "ifsc_prefix": "CBIN"
    }
}

# Regional name mappings for Level 3 realism
REGIONAL_NAMES = {
    "North": {
        "states": ["Delhi", "Punjab", "Haryana", "UP", "Rajasthan"],
        "surnames": ["Sharma", "Singh", "Verma", "Gupta", "Agarwal", "Malhotra", "Kumar", "Yadav", "Chauhan", "Rajput"],
        "first_names_male": ["Rajesh", "Amit", "Vikram", "Rahul", "Suresh", "Manoj", "Sanjay", "Pawan", "Deepak", "Anil"],
        "first_names_female": ["Priya", "Anjali", "Neha", "Pooja", "Sunita", "Meena", "Kavita", "Rekha", "Sunita", "Geeta"]
    },
    "South": {
        "states": ["Tamil Nadu", "Karnataka", "Kerala", "Andhra", "Telangana"],
        "surnames": ["Iyer", "Iyengar", "Reddy", "Nair", "Menon", "Gowda", "Pillai", "Rao", "Krishnan", "Subramaniam"],
        "first_names_male": ["Karthik", "Arun", "Venkatesh", "Ramesh", "Suresh", "Mohan", "Krishna", "Prasad", "Murugan", "Ganesh"],
        "first_names_female": ["Lakshmi", "Parvathi", "Saraswati", "Meenakshi", "Kavya", "Divya", "Swathi", "Anitha", "Radha", "Padma"]
    },
    "West": {
        "states": ["Maharashtra", "Gujarat", "Goa", "Rajasthan"],
        "surnames": ["Patil", "Deshmukh", "Shah", "Mehta", "Joshi", "Desai", "Kulkarni", "Pawar", "Jadhav", "More"],
        "first_names_male": ["Sachin", "Rohit", "Viraj", "Nilesh", "Prashant", "Sandeep", "Ashish", "Ganesh", "Mahesh", "Prakash"],
        "first_names_female": ["Sneha", "Swati", "Archana", "Nisha", "Pallavi", "Vaishali", "Jyoti", "Madhuri", "Urmila", "Shweta"]
    },
    "East": {
        "states": ["West Bengal", "Odisha", "Bihar", "Jharkhand", "Assam"],
        "surnames": ["Banerjee", "Chatterjee", "Das", "Ghosh", "Mukherjee", "Roy", "Bose", "Sen", "Dutta", "Chakraborty"],
        "first_names_male": ["Soumya", "Debashish", "Anirban", "Rajat", "Sourav", "Arijit", "Subham", "Rahul", "Amit", "Sanjay"],
        "first_names_female": ["Srabani", "Ananya", "Sohini", "Riya", "Piya", "Moumita", "Sudeshna", "Kalyani", "Mitali", "Tumpa"]
    }
}