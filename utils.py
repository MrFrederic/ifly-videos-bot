from datetime import datetime
import re
import logging

log = logging.getLogger(__name__)

def parse_filename(filename: str) -> tuple:
    """
    Parse the filename to extract camera name, session and date.
    Returns: (date_timestamp, time_slot, flight_number, camera_name)
    """
    try:
        filename = filename.replace('-', '_')
        parts = filename.split('_')
        
        # Accept two patterns:
        # Pattern A (9 parts): prefix Camera Flight YYYY MM DD HH MM extra
        # Pattern B (>=11 parts): more verbose names containing a detectable year token
        if len(parts) == 9 and re.fullmatch(r"20\d{2}", parts[4]):
            # ifly_Door_F001_2025_08_21_14_30_001.mp4
            camera_name = parts[1]
            flight_number = parts[2] if parts[2].startswith('F') else parts[3]
            year, month, day = parts[4:7]
            hour, minute = parts[7:9]
        else:
            # Fallback generic detection
            year_index = None
            for i, p in enumerate(parts):
                if re.fullmatch(r"20\d{2}", p):
                    year_index = i
                    break
            if year_index is None or year_index + 4 >= len(parts):
                raise ValueError("Could not locate date components in filename")
            camera_name = parts[1]
            flight_number = parts[2] if parts[2].startswith('F') else parts[3]
            year, month, day = parts[year_index:year_index+3]
            hour, minute = parts[year_index+3:year_index+5]

        date = int(datetime.strptime(f"{year}_{month}_{day}", '%Y_%m_%d').timestamp())
        time_slot = get_time_slot(f"{hour}_{minute}")
        
        return date, time_slot, flight_number, camera_name
    except Exception as e:
        log.error(f"Error parsing filename '{filename}': {e}")
        raise

def get_time_slot(input_time: str) -> str:
    """Convert time to 30-minute slots."""
    try:
        hours, minutes = map(int, input_time.split('_'))
        
        if minutes < 30:
            minutes = 0
        else:
            minutes = 30

        return f"{hours:02d}:{minutes:02d}"
    except Exception as e:
        log.error(f"Error getting time slot from '{input_time}': {e}")
        raise

def format_date(timestamp: int) -> str:
    """Format timestamp to readable date."""
    return datetime.fromtimestamp(timestamp).strftime('%d.%m.%Y')

def format_flight_time(seconds: int) -> str:
    """Format flight time to readable format."""
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m"
    elif minutes > 0:
        return f"{minutes}:{seconds:02d} min"
    else:
        return f"{seconds}s"

def format_days_count(days: float) -> str:
    """Format days count to readable format."""
    days = round(days)
    years, remainder = divmod(days, 365)
    months, days_remainder = divmod(remainder, 30)
    
    if years > 0:
        return f"{years} year{'s' if years > 1 else ''}"
    elif months > 0:
        return f"{months} month{'s' if months > 1 else ''}"
    else:
        return f"{days_remainder} day{'s' if days_remainder != 1 else ''}"

def escape_markdown(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2."""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', str(text))
