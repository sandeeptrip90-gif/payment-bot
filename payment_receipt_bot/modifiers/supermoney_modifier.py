"""
SuperMoney HTML Modifier.
"""
from .base_modifier import BaseModifier


class SuperMoneyModifier(BaseModifier):
    app_name = "super.money"

    def build_placeholders(self, data):
        amount = data["amount"]
        return {
            "recipient": data["receiver_name"],
            "amount": f"{amount:,}",
            "date": data["datetime_formatted"],
            "bank": data["payer_bank"],
            "account": data["receiver_account"],
            "upi_id": data["receiver_upi"],
            "transaction_id": data["utr"],
        }
