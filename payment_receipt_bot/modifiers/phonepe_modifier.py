"""
PhonePe HTML Modifier.
"""
from .base_modifier import BaseModifier


class PhonePeModifier(BaseModifier):
    app_name = "PhonePe"

    def build_placeholders(self, data):
        amount = data["amount"]
        return {
            "recipient": data["receiver_name"],
            "amount": f"{amount:,}",
            "date": data["datetime_formatted"],
            "bank": data["payer_bank"],
            "upi_id": data["payer_upi"],
            "transaction_id": data["utr"],
        }
