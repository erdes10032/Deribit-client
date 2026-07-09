ALLOWED_INTERVALS_MINUTES = (5, 10, 15, 30, 60)
DEFAULT_INTERVAL_SECONDS = 600


def minutes_to_seconds(minutes: int) -> int:
    return minutes * 60


def is_valid_interval_minutes(minutes: int) -> bool:
    return minutes in ALLOWED_INTERVALS_MINUTES


def format_interval(seconds: int) -> str:
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} мин"
    hours = minutes // 60
    return f"{hours} ч"
