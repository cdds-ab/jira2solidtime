from datetime import datetime, timedelta
from typing import Tuple
import calendar


def parse_date_range(date_input: str) -> Tuple[datetime, datetime]:
    """
    Parse flexible date range input.

    Supported formats:
    - "YYYY-MM-DD - YYYY-MM-DD" (explicit range)
    - "YYYY-MM-DD" (single day)
    - "YYYY-MM" (entire month)

    Args:
        date_input: Date string in one of the supported formats

    Returns:
        Tuple of (start_date, end_date)
    """
    date_input = date_input.strip()

    # Range format: "2025-09-01 - 2025-09-30"
    if " - " in date_input:
        start_str, end_str = date_input.split(" - ", 1)
        start_date = datetime.strptime(start_str.strip(), "%Y-%m-%d")
        end_date = datetime.strptime(end_str.strip(), "%Y-%m-%d")
        return start_date, end_date

    # Month format: "2025-09"
    elif len(date_input) == 7 and date_input.count("-") == 1:
        year_str, month_str = date_input.split("-")
        year, month = int(year_str), int(month_str)

        # First day of month
        start_date = datetime(year, month, 1)

        # Last day of month
        _, last_day = calendar.monthrange(year, month)
        end_date = datetime(year, month, last_day)

        return start_date, end_date

    # Single day format: "2025-09-16"
    elif len(date_input) == 10 and date_input.count("-") == 2:
        date = datetime.strptime(date_input, "%Y-%m-%d")
        return date, date

    else:
        raise ValueError(
            f"Invalid date format: '{date_input}'. "
            "Use 'YYYY-MM-DD', 'YYYY-MM', or 'YYYY-MM-DD - YYYY-MM-DD'"
        )


def parse_days_back(days: int) -> Tuple[datetime, datetime]:
    """
    Parse days back from today.

    Args:
        days: Number of days back from today

    Returns:
        Tuple of (start_date, end_date)
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    return start_date, end_date


def get_current_month() -> Tuple[datetime, datetime]:
    """
    Get the current month date range.

    Returns:
        Tuple of (start_date, end_date) for current month
    """
    now = datetime.now()
    year = now.year
    month = now.month

    # First day of current month
    start_date = datetime(year, month, 1)

    # Last day of current month
    _, last_day = calendar.monthrange(year, month)
    end_date = datetime(year, month, last_day)

    return start_date, end_date
