"""
Setup script to install dependencies and initialize bot
"""
import subprocess
import sys
import os
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
PACKAGE_DIR = PROJECT_DIR / "payment_receipt_bot"


def install_requirements():
    """Install Python dependencies"""
    print("📦 Installing Python dependencies...")
    requirements = PACKAGE_DIR / "requirements.txt"
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(requirements)])
    
    # Install Playwright browsers
    print("🌐 Installing Playwright browsers...")
    subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])


def create_directories():
    """Create necessary directories"""
    dirs = [
        "data",
        "html_templates",
        "snapshots",
        "modifiers",
        "engines",
        "utils"
    ]
    
    for dir_name in dirs:
        directory = PACKAGE_DIR / dir_name
        directory.mkdir(parents=True, exist_ok=True)
        print(f"✅ Created directory: {directory.relative_to(PROJECT_DIR)}")


def create_sample_data():
    """Create sample Indian names database"""
    sample_names = {
        "male": [
            "Rajesh Kumar", "Amit Sharma", "Rahul Verma", "Vikram Singh",
            "Suresh Reddy", "Manoj Patil", "Sanjay Gupta", "Pawan Kumar",
            "Deepak Agarwal", "Anil Joshi", "Karthik Iyer", "Arun Nair",
            "Venkatesh Rao", "Ramesh Menon", "Sachin Deshmukh", "Rohit Shah"
        ],
        "female": [
            "Priya Sharma", "Anjali Singh", "Neha Gupta", "Pooja Verma",
            "Sunita Kumar", "Meena Reddy", "Kavita Patil", "Rekha Joshi",
            "Lakshmi Iyer", "Parvathi Nair", "Sneha Deshmukh", "Swati Shah"
        ]
    }
    
    import json
    data_file = PACKAGE_DIR / "data" / "indian_names.json"
    with data_file.open('w', encoding='utf-8') as f:
        json.dump(sample_names, f, indent=2, ensure_ascii=False)
    
    print("✅ Created sample names database")


def main():
    print(" Setting up Payment Receipt Bot...\n")
    
    create_directories()
    install_requirements()
    create_sample_data()
    
    print("\n" + "="*50)
    print("✅ Setup complete!")
    print("\nNext steps:")
    print("1. Get Telegram bot token from @BotFather")
    print("2. Edit bot_config.json with your token and user ID")
    print("3. Place your HTML templates in html_templates/ folder")
    print("4. Run: python bot.py")
    print("="*50)


if __name__ == "__main__":
    main()