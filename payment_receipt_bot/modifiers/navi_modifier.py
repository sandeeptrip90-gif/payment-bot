"""
Navi UPI HTML Modifier.
"""
from .base_modifier import BaseModifier


class NaviModifier(BaseModifier):
    app_name = "Navi UPI"

    def build_placeholders(self, data):
        amount = data["amount"]
        return {
            "recipient": data["receiver_name"],
            "amount": f"{amount:,}",
            "date": data["datetime_formatted"],
            "bank": data["payer_bank"],
            "account": data["payer_account"],
            "upi_id": data["payer_upi"],
            "transaction_id": data["utr"],
        }
