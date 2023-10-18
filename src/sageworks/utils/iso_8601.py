"""Helper functions for working with ISO-8601 formatted dates and times"""

from datetime import datetime, date, timezone
import numpy as np
import logging

log = logging.getLogger("sageworks")


def datetime_to_iso8601(datetime_obj) -> str:
    """Convert datetime or date to string in UTC format (yyyy-MM-dd'T'HH:mm:ss.SSSZ)
    Args:
        datetime_obj (datetime/date): The datetime or date object to convert
    Returns:
        str: The datetime as a string in ISO-8601 format
    Note: This particular format is required by AWS Feature Store
    """

    # Check for valid input
    if not isinstance(datetime_obj, (datetime, date)):
        log.error("Invalid input: Expected datetime or date object")
        return None

    # Convert date to datetime if needed
    if isinstance(datetime_obj, date) and not isinstance(datetime_obj, datetime):
        log.info("Received date object; converting to datetime at midnight UTC.")
        datetime_obj = datetime.combine(datetime_obj, datetime.min.time()).replace(tzinfo=timezone.utc)

    # Check for TimeZone
    if datetime_obj.tzinfo is None:
        log.warning("Datetime object is naive; localizing to UTC.")
        datetime_obj = datetime_obj.replace(tzinfo=timezone.utc)

    try:
        # Convert to ISO-8601 String
        iso_str = datetime_obj.astimezone(timezone.utc).isoformat("T", "milliseconds")
        return iso_str.replace("+00:00", "Z")
    except Exception as e:
        log.error(f"Failed to convert datetime to ISO-8601 string: {e}")
        return None


def iso8601_to_datetime(iso8601_str: str) -> datetime:
    """Convert ISO-8601 string to datetime object
    Args:
        iso8601_str (str): The ISO-8601 string to convert
    Returns:
        datetime: The datetime object
    """
    if "Z" in iso8601_str:
        iso8601_str = iso8601_str.replace("Z", "+00:00")
    return datetime.fromisoformat(iso8601_str).replace(tzinfo=timezone.utc)


def convert_all_to_iso8601(data):
    """Convert datetime fields to ISO-8601 string
    Args:
        data (arbitrary type): The data to convert
    Returns:
        arbitrary type: The converted data
    """
    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            result[key] = convert_all_to_iso8601(value)
        return result
    elif isinstance(data, list):
        result = []
        for item in data:
            result.append(convert_all_to_iso8601(item))
        return result
    elif isinstance(data, datetime):
        return datetime_to_iso8601(data)
    elif isinstance(data, np.int64):
        return int(data)
    else:
        return data


if __name__ == "__main__":
    """Exercise the helper functions"""

    # Test the conversion to ISO-8601
    now = datetime.now(timezone.utc)
    print(now)
    now_str = datetime_to_iso8601(now)
    print(now_str)

    # Test the conversion from ISO-8601 back to datetime
    now2 = iso8601_to_datetime(now_str)
    print(now2)

    # Test the conversion of all datetime fields to ISO-8601
    data = {"a": 1, "b": "2", "c": now, "d": {"e": 3, "f": now}}
    print(data)
    data2 = convert_all_to_iso8601(data)
    print(data2)
