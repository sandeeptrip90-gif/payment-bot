"""Interactive setup: create bot_config.json with a Telegram token and admin user ID."""
import json
import sys
from pathlib import Path

CFG_PATH = Path(__file__).resolve().parent / "bot_config.json"


def prompt(question: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{question}{suffix}: ").strip()
    return value or default


def main() -> None:
    if CFG_PATH.exists():
        try:
            existing = json.loads(CFG_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}
        print(f"Existing config found at {CFG_PATH}")
        token = prompt("Telegram bot token", existing.get("telegram_token", ""))
        try:
            admin_id = int(prompt("Admin user ID", str(existing.get("admin_user_id", ""))))
        except ValueError:
            print("Admin user ID must be an integer.", file=sys.stderr)
            sys.exit(1)
    else:
        print("Creating new bot_config.json")
        print("Get a token from @BotFather on Telegram.")
        token = prompt("Telegram bot token")
        if not token:
            print("Token is required.", file=sys.stderr)
            sys.exit(1)
        try:
            admin_id = int(prompt("Admin user ID"))
        except ValueError:
            print("Admin user ID must be an integer.", file=sys.stderr)
            sys.exit(1)

    cfg = {
        "telegram_token": token,
        "admin_user_id": admin_id,
    }
    CFG_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {CFG_PATH}")
    print("Run: python run.py")


if __name__ == "__main__":
    main()
