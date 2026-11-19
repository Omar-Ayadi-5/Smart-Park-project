from datetime import datetime, timezone


def utc_now():
    """Naive UTC for the existing timestamp-without-time-zone schema."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
