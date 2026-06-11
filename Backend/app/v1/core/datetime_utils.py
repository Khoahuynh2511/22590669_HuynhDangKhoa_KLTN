from datetime import date, datetime
from typing import Any, Optional


def to_json_value(value: Any) -> Optional[str]:
    """Convert date/datetime values to JSON-safe strings."""
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)
