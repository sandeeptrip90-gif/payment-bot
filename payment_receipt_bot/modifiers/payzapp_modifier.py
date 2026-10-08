"""
PayZapp HTML Modifier.
"""
from .base_modifier import BaseModifier


class PayZappModifier(BaseModifier):
    app_name = "PayZapp"

    def build_placeholders(self, data):
        amount = data["amount"]
        return {
            "recipient": data["receiver_name"],
            "amount": f"{amount:,}",
            "date": data["datetime_formatted"],
            "bank": data["payer_bank"],
            "upi_id": data["receiver_upi"],
            "transaction_id": data["utr"],
        }
