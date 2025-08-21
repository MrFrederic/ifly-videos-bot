from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from utils import format_date, escape_markdown
import logging

log = logging.getLogger(__name__)

def generate_tree_text(organized_data: dict, day_index: int = None, session_index: int = None) -> str:
    """Generate the tree view text for video library."""
    try:
        tree_text = ["━━━━━━━━━━━━━━━━", "📦 *Library*"]

        days = organized_data.get('days', [])
        for day_idx, day in enumerate(days):
            line_parts = []
            # Branch/leaf symbol
            line_parts.append("└── " if day_idx + 1 == len(days) else "├── ")
            # Folder icon and optional bold
            if day_index == day_idx:
                line_parts.append("📂 *" + escape_markdown(format_date(day['date'])) + "*")
            else:
                line_parts.append("📁 " + escape_markdown(format_date(day['date'])))
            tree_text.append(''.join(line_parts))

            if day_index == day_idx:
                sessions = day.get('sessions', [])
                for sess_idx, session in enumerate(sessions):
                    sess_line = []
                    # Vertical connector spacing
                    sess_line.append("    " if day_idx + 1 == len(days) else "│   ")
                    # Branch/leaf for session
                    sess_line.append("└── " if sess_idx + 1 == len(sessions) else "├── ")
                    flights_count = len(session.get('flights', []))
                    sess_line.append(f"🕐 {escape_markdown(session['time_slot'])} \\({flights_count} flight{'s' if flights_count != 1 else ''}\\)")
                    tree_text.append(''.join(sess_line))

        tree_text.append("━━━━━━━━━━━━━━━━")
        return "\n".join(tree_text)
    except Exception as e:
        log.error(f"Error generating tree text: {e}")
        return "Error generating library view"

def create_navigation_keyboard(organized_data: dict, day_index: int = None, session_index: int = None) -> InlineKeyboardMarkup:
    """Create navigation keyboard for the tree view."""
    keyboard = []
    
    if day_index is None:
        # Main library view - show day buttons
        days = organized_data.get('days', [])
        for day_idx, day in enumerate(days):
            date_str = format_date(day['date'])
            sessions_count = len(day.get('sessions', []))
            button_text = f"📁 {date_str} ({sessions_count} sessions)"
            keyboard.append([
                InlineKeyboardButton(button_text, callback_data=f"nav:day:{day_idx}")
            ])
        
        keyboard.append([
            InlineKeyboardButton("← Back", callback_data="home")
        ])
    else:
        # Day view - show sessions
        day = organized_data['days'][day_index]
        sessions = day.get('sessions', [])
        
        # Session buttons (max 2 per row)
        session_buttons = []
        for sess_idx, session in enumerate(sessions):
            flights_count = len(session.get('flights', []))
            button_text = f"{session['time_slot']} ({flights_count})"
            session_buttons.append(
                InlineKeyboardButton(button_text, callback_data=f"nav:session:{day_index}:{sess_idx}")
            )
        
        # Arrange session buttons in rows of 2
        for i in range(0, len(session_buttons), 2):
            row = session_buttons[i:i+2]
            keyboard.append(row)
        
        # Navigation buttons
        keyboard.append([
            InlineKeyboardButton("← Back", callback_data="nav:library"),
            InlineKeyboardButton("🏠 Home", callback_data="home")
        ])
    
    return InlineKeyboardMarkup(keyboard)

def create_session_view_keyboard(organized_data: dict, day_index: int, session_index: int) -> InlineKeyboardMarkup:
    """Create keyboard for session view showing flights."""
    keyboard = []
    
    day = organized_data['days'][day_index]
    session = day['sessions'][session_index]
    flights = session.get('flights', [])
    
    # Flight buttons
    for flight_idx, flight in enumerate(flights):
        videos_count = len(flight.get('videos', []))
        button_text = f"Flight {flight['flight_number']} ({videos_count} videos)"
        keyboard.append([
            InlineKeyboardButton(button_text, callback_data=f"nav:flight:{day_index}:{session_index}:{flight_idx}")
        ])
    
    # Navigation buttons
    keyboard.append([
        InlineKeyboardButton("← Back", callback_data=f"nav:day:{day_index}"),
        InlineKeyboardButton("🏠 Home", callback_data="home")
    ])
    
    return InlineKeyboardMarkup(keyboard)

def create_flight_view_keyboard(organized_data: dict, day_index: int, session_index: int, flight_index: int, current_video: int = 0) -> InlineKeyboardMarkup:
    """Create keyboard for flight view showing videos."""
    keyboard = []
    
    day = organized_data['days'][day_index]
    session = day['sessions'][session_index]
    flight = session['flights'][flight_index]
    videos = flight.get('videos', [])
    
    # Video selection buttons
    video_buttons = []
    for video_idx, video in enumerate(videos):
        if video_idx == current_video:
            button_text = f"● {video['camera_name']}"
        else:
            button_text = video['camera_name']
        
        video_buttons.append(
            InlineKeyboardButton(button_text, callback_data=f"video:{day_index}:{session_index}:{flight_index}:{video_idx}")
        )
    
    # Arrange video buttons in rows of 2
    for i in range(0, len(video_buttons), 2):
        row = video_buttons[i:i+2]
        keyboard.append(row)
    
    # Navigation buttons
    keyboard.append([
        InlineKeyboardButton("← Back", callback_data=f"nav:session:{day_index}:{session_index}"),
        InlineKeyboardButton("🏠 Home", callback_data="home")
    ])

    # Delete buttons (two-step confirmation)
    current_video_obj = videos[current_video] if videos else None
    if current_video_obj:
        keyboard.append([
            InlineKeyboardButton("🗑️ Delete", callback_data=f"del:ask:{day_index}:{session_index}:{flight_index}:{current_video}:{current_video_obj['id']}")
        ])
    
    return InlineKeyboardMarkup(keyboard)
