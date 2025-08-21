#!/usr/bin/env python3
"""
Test script for iFLY Videos Bot
This script verifies that all components work correctly.
"""

import sys
import os
from pathlib import Path

def test_imports():
    """Test that all required modules can be imported."""
    print("Testing imports...")
    try:
        import sqlite3  # noqa: F401
        from datetime import datetime  # noqa: F401
        print("✅ Standard library imports work")
    except ImportError as e:
        print(f"❌ Standard library import failed: {e}")
        return False

    try:
        from config import Config
        from database import Database
        from utils import parse_filename, format_flight_time
        print("✅ Local module imports work")
    except ImportError as e:
        print(f"❌ Local module import failed: {e}")
        return False
    
    return True

def test_config():
    """Test environment configuration loading."""
    print("\nTesting configuration...")
    try:
        # Set env vars
        os.environ["TELEGRAM_BOT_TOKEN"] = "test_token"
        os.environ["TELEGRAM_IFLY_CHAT_ID"] = "123456789"
        os.environ["DATABASE_PATH"] = "./data/test.db"
        os.environ["SESSION_LENGTH_MINUTES"] = "30"
        os.environ["LOG_LEVEL"] = "INFO"

        from config import Config
        config = Config()

        assert config.bot_token == "test_token"
        assert config.ifly_chat_id == 123456789
        assert config.session_length_minutes == 30
        assert config.database_path.endswith("test.db")

        print("✅ Configuration loading works")
        return True
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def test_database():
    """Test database operations."""
    print("\nTesting database...")
    try:
        from database import Database
        
        # Create test database
        db = Database("./data/test_videos.db")
        
        # Test user operations
        success = db.add_user(12345, "testuser")
        assert success, "Failed to add user"
        
        user = db.get_user_by_chat_id(12345)
        assert user is not None, "Failed to retrieve user"
        assert user['username'] == "testuser"
        
        # Test video operations
        success = db.add_video(12345, "test_file_id", "ifly_Door_F001_2025_08_21_14_30_001.mp4", 
                              60, 1724256000, "14:30", "F001", "Door")
        assert success, "Failed to add video"
        
        videos = db.get_videos_by_user(12345)
        assert len(videos) == 1, "Failed to retrieve videos"
        
        # Cleanup
        Path("./data/test_videos.db").unlink(missing_ok=True)
        
        print("✅ Database operations work")
        return True
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def test_utils():
    """Test utility functions."""
    print("\nTesting utilities...")
    try:
        from utils import parse_filename, format_flight_time, format_days_count

        # Test filename parsing
        fname = "ifly_Door_F001_2025_08_21_14_30_001.mp4"
        date, time_slot, flight_number, camera_name = parse_filename(fname)
        print('Parsed filename ->', date, time_slot, flight_number, camera_name)
        assert camera_name == "Door", f"camera_name mismatch: {camera_name}"
        assert flight_number == "F001", f"flight_number mismatch: {flight_number}"
        assert time_slot == "14:30", f"time_slot mismatch: {time_slot}"

        # Test time formatting
        formatted = format_flight_time(3661)  # 1 hour, 1 minute, 1 second
        print('Formatted flight time ->', formatted)
        assert "1h" in formatted, f"formatted time missing hour: {formatted}"

        # Test days formatting
        days_text = format_days_count(45)
        print('Formatted days count ->', days_text)
        assert any(k in days_text.lower() for k in ("day", "month", "year")), f"unexpected days text: {days_text}"

        print("✅ Utility functions work")
        return True
    except Exception as e:
        print(f"❌ Utility test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Running iFLY Videos Bot Tests")
    print("=" * 40)
    
    tests = [test_imports, test_config, test_database, test_utils]
    passed = 0
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n📊 Results: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("🎉 All tests passed! The bot should work correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
