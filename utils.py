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
        
        # Pattern A (legacy, 9 parts after replacement): prefix Camera Flight YYYY MM DD HH MM extra
        # Example: ifly_Door_F001_2025_08_21_14_30_001.mp4
        if len(parts) == 9 and re.fullmatch(r"20\d{2}", parts[4]):
            camera_name = parts[1]
            flight_number = parts[2] if parts[2].startswith('F') else parts[3]
            year, month, day = parts[4:7]
            hour, minute = parts[7:9]
        # Pattern B (current long form, >=10 parts): Location Event Camera Flight YYYY MM DD HH MM SS
        # Example original: iFlyMinsk_iFLYPROEvents_Door_10_2025-08-17_21-30-33.mp4
        # After replacement: iFlyMinsk_iFLYPROEvents_Door_10_2025_08_17_21_30_33.mp4
        elif len(parts) >= 10 and re.fullmatch(r"20\d{2}", parts[4]):
            camera_name = parts[2]
            raw_flight = parts[3]
            # Normalize flight number to F### if numeric
            if raw_flight.startswith('F'):
                flight_number = raw_flight
            else:
                # Pad numeric with zeros to maintain ordering, assume up to 3 digits
                flight_number = f"F{int(raw_flight):03d}" if raw_flight.isdigit() else raw_flight
            year, month, day = parts[4:7]
            hour, minute = parts[7:9]
        else:
            # Generic fallback: find year token anywhere
            year_index = next((i for i,p in enumerate(parts) if re.fullmatch(r"20\d{2}", p)), None)
            if year_index is None or year_index + 4 >= len(parts):
                raise ValueError("Could not locate date components in filename")
            # Heuristic: camera likely immediately before flight or at index 1
            # We try to detect camera by known names
            known_cameras = {"Door", "Centerline", "Firsttimer", "Sideline"}
            camera_name = next((p for p in parts if p in known_cameras), parts[1])
            # Flight number: token starting with F or numeric near camera
            flight_number = next((p for p in parts if p.startswith('F') and len(p) <= 5), None)
            if not flight_number:
                # numeric token just before year maybe
                cand = parts[year_index - 1] if year_index - 1 >= 0 else '1'
                flight_number = f"F{int(cand):03d}" if cand.isdigit() else cand
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
