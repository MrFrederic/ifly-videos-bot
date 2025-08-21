import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathlib import Path

class Database:
    """Database operations for the iFLY videos bot."""
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_connection()
    
    def _ensure_connection(self):
        """Ensure database file and schema exist (idempotent)."""
        # Always (re)apply schema to ensure required tables exist
        self._initialize_schema()

    def _initialize_schema(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # Users table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        # Videos table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_chat_id INTEGER NOT NULL,
                file_id TEXT NOT NULL,
                file_name TEXT NOT NULL,
                duration INTEGER NOT NULL,
                flight_date INTEGER NOT NULL,
                time_slot TEXT NOT NULL,
                flight_number TEXT NOT NULL,
                camera_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_chat_id) REFERENCES users (chat_id),
                UNIQUE(file_name, user_chat_id)
            )
            """
        )
        # Sessions table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_chat_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                expires_at INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        # System data
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS system_data (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
        # Perform migrations after ensuring base schema
        try:
            self._migrate_videos_unique_constraint(conn)
        except Exception as e:
            print(f"Migration warning: {e}")
        conn.close()

    def _migrate_videos_unique_constraint(self, conn):
        """Migrate videos table UNIQUE(file_name,user_chat_id) -> UNIQUE(file_id,user_chat_id)."""
        cursor = conn.cursor()
        # Detect existing indexes referencing file_name & user_chat_id as unique combo
        cursor.execute("PRAGMA index_list(videos)")
        indexes = cursor.fetchall()
        needs_migration = False
        for idx in indexes:
            idx_name = idx[1]
            cursor.execute("PRAGMA index_info(%s)" % idx_name)
            cols = [r[2] for r in cursor.fetchall()]
            if set(cols) == {"file_name", "user_chat_id"}:
                # confirm uniqueness changed target
                needs_migration = True
                break
        if not needs_migration:
            return
        # Rebuild table
        cursor.execute("BEGIN TRANSACTION")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS videos_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_chat_id INTEGER NOT NULL,
                file_id TEXT NOT NULL,
                file_name TEXT NOT NULL,
                duration INTEGER NOT NULL,
                flight_date INTEGER NOT NULL,
                time_slot TEXT NOT NULL,
                flight_number TEXT NOT NULL,
                camera_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_chat_id) REFERENCES users (chat_id),
                UNIQUE(file_id, user_chat_id)
            )
            """
        )
        cursor.execute(
            """
            INSERT OR IGNORE INTO videos_new (id,user_chat_id,file_id,file_name,duration,flight_date,time_slot,flight_number,camera_name,created_at)
            SELECT id,user_chat_id,file_id,file_name,duration,flight_date,time_slot,flight_number,camera_name,created_at FROM videos
            """
        )
        cursor.execute("DROP TABLE videos")
        cursor.execute("ALTER TABLE videos_new RENAME TO videos")
        cursor.execute("COMMIT")
    
    def get_connection(self):
        """Get database connection."""
        return sqlite3.connect(self.db_path)
    
    # User operations
    def add_user(self, chat_id: int, username: str = None) -> bool:
        """Add or update user."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO users (chat_id, username)
                VALUES (?, ?)
            ''', (chat_id, username))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error adding user: {e}")
            return False
        finally:
            conn.close()
    
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Get user by username."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT chat_id, username FROM users WHERE LOWER(username) = LOWER(?)', (username,))
            row = cursor.fetchone()
            if row:
                return {'chat_id': row[0], 'username': row[1]}
            return None
        finally:
            conn.close()
    
    def get_user_by_chat_id(self, chat_id: int) -> Optional[Dict]:
        """Get user by chat_id."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT chat_id, username FROM users WHERE chat_id = ?', (chat_id,))
            row = cursor.fetchone()
            if row:
                return {'chat_id': row[0], 'username': row[1]}
            return None
        finally:
            conn.close()
    
    # Video operations
    def add_video(self, user_chat_id: int, file_id: str, file_name: str, duration: int,
                  flight_date: int, time_slot: str, flight_number: str, camera_name: str) -> bool:
        """Add video to database."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO videos 
                (user_chat_id, file_id, file_name, duration, flight_date, time_slot, flight_number, camera_name)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_chat_id, file_id, file_name, duration, flight_date, time_slot, flight_number, camera_name))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error adding video: {e}")
            return False
        finally:
            conn.close()

    def delete_video_by_id(self, user_chat_id: int, video_id: int) -> bool:
        """Delete a single video by its DB id for a user."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                DELETE FROM videos WHERE user_chat_id = ? AND id = ?
            ''', (user_chat_id, video_id))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error deleting video by id: {e}")
            return False
        finally:
            conn.close()
    
    def get_videos_by_user(self, chat_id: int) -> List[Dict]:
        """Get all videos for a user organized by date and session."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT id, flight_date, time_slot, flight_number, camera_name, file_id, file_name, duration
                FROM videos
                WHERE user_chat_id = ?
                ORDER BY flight_date, time_slot, flight_number, 
                    CASE camera_name 
                        WHEN 'Door' THEN 1
                        WHEN 'Centerline' THEN 2
                        WHEN 'Firsttimer' THEN 3
                        WHEN 'Sideline' THEN 4
                        ELSE 5
                    END
            ''', (chat_id,))
            
            videos = []
            for row in cursor.fetchall():
                videos.append({
                    'id': row[0],
                    'flight_date': row[1],
                    'time_slot': row[2],
                    'flight_number': row[3],
                    'camera_name': row[4],
                    'file_id': row[5],
                    'file_name': row[6],
                    'duration': row[7]
                })
            return videos
        finally:
            conn.close()
    
    def get_organized_videos(self, chat_id: int) -> Dict:
        """Get videos organized in the same structure as the legacy system."""
        videos = self.get_videos_by_user(chat_id)
        organized = {'days': []}
        
        days_dict = {}
        
        for video in videos:
            date = video['flight_date']
            time_slot = video['time_slot']
            flight_number = video['flight_number']
            
            # Get or create day
            if date not in days_dict:
                days_dict[date] = {'date': date, 'sessions': []}
            
            day = days_dict[date]
            
            # Get or create session
            session = next((s for s in day['sessions'] if s['time_slot'] == time_slot), None)
            if not session:
                session = {'time_slot': time_slot, 'flights': []}
                day['sessions'].append(session)
            
            # Get or create flight
            flight = next((f for f in session['flights'] if f['flight_number'] == flight_number), None)
            if not flight:
                flight = {'flight_number': flight_number, 'length': video['duration'], 'videos': []}
                session['flights'].append(flight)
            
            # Add video
            flight['videos'].append({
                'id': video['id'],
                'camera_name': video['camera_name'],
                'file_id': video['file_id'],
                'file_name': video['file_name']
            })
        
        # Sort everything
        organized['days'] = sorted(days_dict.values(), key=lambda x: x['date'])
        for day in organized['days']:
            day['sessions'].sort(key=lambda x: x['time_slot'])
            for session in day['sessions']:
                session['flights'].sort(key=lambda x: x['flight_number'])
        
        return organized
    
    def get_user_stats(self, chat_id: int) -> Dict:
        """Get user statistics."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # Total flight time
            cursor.execute('SELECT SUM(duration) FROM videos WHERE user_chat_id = ?', (chat_id,))
            total_time = cursor.fetchone()[0] or 0
            
            # Days since first flight
            cursor.execute('SELECT MIN(flight_date) FROM videos WHERE user_chat_id = ?', (chat_id,))
            first_flight = cursor.fetchone()[0]
            days_since_first = 0
            if first_flight:
                days_since_first = (datetime.now().timestamp() - first_flight) / 86400
            
            return {
                'total_flight_time': total_time,
                'days_since_first_flight': days_since_first
            }
        finally:
            conn.close()
    
    # Session operations
    def create_session(self, target_chat_id: int, username: str, duration_minutes: int) -> bool:
        """Create authentication session."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            expires_at = int((datetime.now() + timedelta(minutes=duration_minutes)).timestamp())
            cursor.execute('''
                INSERT OR REPLACE INTO sessions (target_chat_id, username, expires_at)
                VALUES (?, ?, ?)
            ''', (target_chat_id, username, expires_at))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error creating session: {e}")
            return False
        finally:
            conn.close()
    
    def get_active_session(self) -> Optional[Dict]:
        """Get active session if any."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            now = int(datetime.now().timestamp())
            cursor.execute('''
                SELECT target_chat_id, username, expires_at
                FROM sessions
                WHERE expires_at > ?
                ORDER BY expires_at DESC
                LIMIT 1
            ''', (now,))
            row = cursor.fetchone()
            if row:
                return {
                    'target_chat_id': row[0],
                    'username': row[1],
                    'expires_at': row[2]
                }
            return None
        finally:
            conn.close()
    
    def end_session(self) -> bool:
        """End current session."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM sessions')
            conn.commit()
            return True
        except Exception as e:
            print(f"Error ending session: {e}")
            return False
        finally:
            conn.close()
    
    # System data operations
    def set_system_value(self, key: str, value: str) -> bool:
        """Set system value."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO system_data (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (key, value))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error setting system value: {e}")
            return False
        finally:
            conn.close()
    
    def get_system_value(self, key: str) -> Optional[str]:
        """Get system value."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT value FROM system_data WHERE key = ?', (key,))
            row = cursor.fetchone()
            return row[0] if row else None
        finally:
            conn.close()
