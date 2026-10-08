from decimal import Decimal


def validate_amount(amount: str | int | float) -> str:
    value = Decimal(str(amount))
    if value <= 0:
        raise ValueError("amount must be greater than zero")
    return f"{value:,.2f}"


def validate_app(app: str, supported_apps: tuple[str, ...]) -> str:
    normalized = app.strip().lower()
    if normalized not in supported_apps:
        raise ValueError(f"unsupported app: {app}")
    return normalized
