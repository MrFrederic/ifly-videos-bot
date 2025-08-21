#!/bin/bash

# iFLY Videos Bot - Quick Setup Script

set -e

echo "🚀 iFLY Videos Bot Setup"
echo "========================"

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Error: docker-compose.yml not found. Are you in the bot directory?"
    exit 1
fi

echo "📝 This version uses environment variables instead of config.yaml"
echo "Set the following variables before running (or edit docker-compose.yml):"
echo "  TELEGRAM_BOT_TOKEN=your_token_here"
echo "  TELEGRAM_IFLY_CHAT_ID=123456789"
echo "  (Optional overrides) DATABASE_PATH, SESSION_LENGTH_MINUTES, LOG_LEVEL"
echo ""

# Create data directory
echo "📁 Ensuring data directory exists..."
mkdir -p data

# Build and start the bot
echo "🐳 Building and starting bot with Docker..."
docker compose up -d --build

echo ""
echo "✅ Bot should now be running!"
echo ""
echo "To check status: docker compose ps"
echo "To view logs: docker compose logs -f ifly-videos-bot"
echo "To stop: docker compose down"
echo ""
echo "Don't forget to:"
echo "1. Add your bot to the iFLY chat"
echo "2. Test the bot by sending /start in a private chat"
