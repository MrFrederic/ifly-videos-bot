# iFLY Videos Bot

A modern Telegram bot for organizing and managing iFLY video files with SQLite database storage and Docker support.

## Features

- **SQLite Database**: Store users and video metadata in a local SQLite database
- **YAML Configuration**: Easy configuration management with YAML files
- **Docker Support**: Containerized application with Docker Compose
- **Video Organization**: Automatically organize videos by date, session, and flight
- **Authentication System**: Secure session-based authentication for iFLY chat uploads
- **User Statistics**: Track flight time and flying history
- **Clean UI**: Intuitive navigation with inline keyboards

## Setup

### Using Docker (Recommended)

1. Clone or copy the bot files to your server
2. Edit environment variables in `docker-compose.yml` (or export them before running):
   - TELEGRAM_BOT_TOKEN (required)
   - TELEGRAM_IFLY_CHAT_ID (required)
   - DATABASE_PATH (optional, default /app/data/videos.db)
   - SESSION_LENGTH_MINUTES (optional, default 30)
   - LOG_LEVEL (optional, default INFO)
3. Build and run with Docker Compose:
   ```bash
   docker compose up -d --build
   ```

### Manual Installation

1. Install Python 3.11+ and required packages:
   ```bash
   pip install -r requirements.txt
   ```
2. Initialize the database:
   ```bash
   python init_db.py
   ```
3. Export required environment variables:
   ```bash
   export TELEGRAM_BOT_TOKEN=YOUR_TOKEN
   export TELEGRAM_IFLY_CHAT_ID=123456789
   # Optional overrides
   export DATABASE_PATH=./data/videos.db
   export SESSION_LENGTH_MINUTES=30
   export LOG_LEVEL=INFO
   ```
4. Initialize the database (creates tables):
   ```bash
   python init_db.py
   ```
5. Run the bot:
   ```bash
   python main.py
   ```

## Configuration

Configure the bot via environment variables:

- TELEGRAM_BOT_TOKEN: Your Telegram bot token from @BotFather
- TELEGRAM_IFLY_CHAT_ID: The chat ID of your iFLY group/channel
- DATABASE_PATH: Path to SQLite database file (default ./data/videos.db)
- SESSION_LENGTH_MINUTES: How long authentication sessions last (default 30)
- LOG_LEVEL: Log level (DEBUG, INFO, WARNING, ERROR; default INFO)

## Usage

### For Users

1. Start a private chat with the bot and send `/start`
2. Upload videos directly to the bot - they will be automatically organized
3. Browse your video library using the menu buttons
4. View your flying statistics

### For iFLY Chat

1. Add the bot to your iFLY chat
2. Send `/start` in the chat to begin authentication
3. Send the username of the person uploading videos
4. Confirm the session start
5. Upload videos - they will be saved to the specified user's library

## File Structure

```
bot/
├── main.py              # Main bot application
├── config.py            # Configuration management
├── database.py          # Database operations
├── utils.py             # Utility functions
├── ui.py                # User interface components
├── init_db.py           # Database initialization
├── requirements.txt     # Python dependencies
├── Dockerfile           # Docker container definition
├── docker-compose.yml   # Docker Compose configuration
├── config.example.yaml  # Example configuration
└── data/                # Database and data files (created at runtime)
```

## Database Schema

The bot uses SQLite with the following tables:

- **users**: Store user information (chat_id, username)
- **videos**: Store video metadata and file references
- **sessions**: Manage authentication sessions for iFLY chat
- **system_data**: Store system configuration and state

## Video File Naming

Videos should follow the naming convention from the legacy system:
`prefix_camera_flight_YYYY_MM_DD_HH_MM_suffix.mp4`

Example: `ifly_Door_F001_2025_08_21_14_30_001.mp4`

## Differences from Legacy System

- **No pinned messages**: Videos are stored in SQLite database instead of JSON in pinned messages
- **YAML configuration**: Replaces environment variables and .env files
- **Dockerized**: Easy deployment with Docker and Docker Compose
- **Cleaner code**: Modern Python practices with proper error handling
- **Better separation**: Modular design with separate files for different concerns

## Troubleshooting

### Bot doesn't start
- Check that required environment variables are set (TELEGRAM_BOT_TOKEN, TELEGRAM_IFLY_CHAT_ID)
- Ensure the bot has necessary permissions in your iFLY chat
- Check logs: `docker-compose logs ifly-videos-bot`

### Videos not uploading
- Verify video file naming follows the expected convention
- Check bot permissions in the chat
- Review logs for parsing errors

### Database issues
- Ensure the `data` directory is writable
- Check that SQLite3 is installed (included in Docker image)
- Database is automatically created if missing
