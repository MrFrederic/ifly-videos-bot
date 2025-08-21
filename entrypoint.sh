#!/bin/bash
set -e

# Ensure data directory exists
mkdir -p /app/data

# Initialize database if it doesn't exist
if [ ! -f /app/data/videos.db ]; then
    echo "Initializing database..."
    python init_db.py
fi

# Execute the main command
exec "$@"
