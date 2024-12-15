# utils/validators.py
import re
from datetime import datetime
from zoneinfo import ZoneInfo
import logging

def is_date(date_str):
    """Checks if a given string is a valid date in various formats."""
    date_str = date_str.strip()  # Remove leading/trailing whitespace
    patterns = [
        r'^(\d{1,2})\.(\d{1,2})\.(\d{4})(\.)?$',  # DD.MM.YYYY or DD.MM.YYYY.
        r'^(\d{1,2})/(\d{1,2})/(\d{4})$',          # DD/MM/YYYY
        r'^(\d{4})-(\d{2})-(\d{2})$'              # YYYY-MM-DD
    ]

    for pattern in patterns:
        match = re.match(pattern, date_str)
        if match:
            try:
                day, month, year = map(int, match.groups()[:3])
                datetime(year, month, day)  #Attempt to create a datetime object.  Raises ValueError if invalid date.
                return True
            except ValueError:
                return False  #Invalid date combination (e.g., Feb 30)

    return False # No matching pattern found

def format_datetime(date_str, time_str):
    """Formats a date and time string into a datetime object with timezone information.  Handles various date formats."""
    date_str = date_str.strip()
    time_str = time_str.strip()
    timezone = ZoneInfo("Europe/Zagreb") # Explicitly set the timezone here

    try:
        # Attempt to parse different date formats
        for fmt in ['%d.%m.%Y.', '%d/%m/%Y', '%Y-%m-%d']:
            try:
                date_obj = datetime.strptime(date_str, fmt).date()
                break  # If successful, exit the loop.
            except ValueError:
                pass  # Try other format
        else:
            raise ValueError(f"Neispravan format datuma: {date_str}")

        #Parse time - ensuring consistent format
        time_obj = datetime.strptime(time_str.replace(".", ":"), '%H:%M').time()

        # Combine date and time, localize with timezone
        datetime_obj = datetime.combine(date_obj, time_obj)
        localized_datetime = datetime_obj.replace(tzinfo=timezone)

        return localized_datetime

    except ValueError as e:
        raise ValueError(f"Neispravan format datuma/vremena: {date_str} {time_str}. Greška: {e}")
    except Exception as e:
        raise Exception(f"Neočekivana greška pri formatiranju datuma/vremena: {e}")