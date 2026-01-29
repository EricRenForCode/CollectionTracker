"""Database module for anonymous user system using SQLite."""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any
from contextlib import contextmanager


class Database:
    """SQLite database manager for anonymous user system."""
    
    def __init__(self, db_path: str = "data/users.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self._init_database()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _init_database(self):
        """Initialize database tables."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create anonymous_users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS anonymous_users (
                    device_id TEXT PRIMARY KEY,
                    fingerprint TEXT NOT NULL,
                    user_data TEXT,
                    created_at INTEGER NOT NULL,
                    last_seen INTEGER NOT NULL,
                    session_count INTEGER DEFAULT 1
                )
            """)
            
            # Create indexes for anonymous_users
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_fingerprint 
                ON anonymous_users(fingerprint)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_last_seen 
                ON anonymous_users(last_seen)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_created_at 
                ON anonymous_users(created_at)
            """)
            
            # Create user_preferences table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT,
                    updated_at INTEGER NOT NULL,
                    FOREIGN KEY (device_id) REFERENCES anonymous_users (device_id)
                )
            """)
            
            # Create unique index for device_id + key
            cursor.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_device_preference 
                ON user_preferences(device_id, key)
            """)
            
            # Create transactions table (migrated from JSON storage)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id TEXT PRIMARY KEY,
                    device_id TEXT NOT NULL,
                    entity TEXT NOT NULL,
                    transaction_type TEXT NOT NULL,
                    amount REAL NOT NULL,
                    description TEXT,
                    timestamp INTEGER NOT NULL,
                    FOREIGN KEY (device_id) REFERENCES anonymous_users (device_id)
                )
            """)
            
            # Create indexes for transactions
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_device_transactions 
                ON transactions(device_id, timestamp DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_entity_transactions 
                ON transactions(device_id, entity, timestamp DESC)
            """)
            
            # Create collections table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS collections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL,
                    entity_name TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    FOREIGN KEY (device_id) REFERENCES anonymous_users (device_id)
                )
            """)
            
            # Create unique index for device_id + entity_name
            cursor.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_device_entity 
                ON collections(device_id, entity_name COLLATE NOCASE)
            """)
    
    # Anonymous Users Operations
    
    def create_user(self, device_id: str, fingerprint: str, user_data: Optional[Dict] = None) -> Dict:
        """Create a new anonymous user."""
        now = int(datetime.now().timestamp())
        user_data_json = json.dumps(user_data or {})
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO anonymous_users 
                (device_id, fingerprint, user_data, created_at, last_seen, session_count)
                VALUES (?, ?, ?, ?, ?, 1)
            """, (device_id, fingerprint, user_data_json, now, now))
        
        return {
            "device_id": device_id,
            "fingerprint": fingerprint,
            "user_data": user_data or {},
            "created_at": now,
            "last_seen": now,
            "session_count": 1
        }
    
    def get_user_by_device_id(self, device_id: str) -> Optional[Dict]:
        """Get user by device_id."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM anonymous_users WHERE device_id = ?
            """, (device_id,))
            row = cursor.fetchone()
            
            if row:
                return {
                    "device_id": row["device_id"],
                    "fingerprint": row["fingerprint"],
                    "user_data": json.loads(row["user_data"]) if row["user_data"] else {},
                    "created_at": row["created_at"],
                    "last_seen": row["last_seen"],
                    "session_count": row["session_count"]
                }
            return None
    
    def get_user_by_fingerprint(self, fingerprint: str) -> Optional[Dict]:
        """Get user by fingerprint."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM anonymous_users 
                WHERE fingerprint = ?
                ORDER BY last_seen DESC
                LIMIT 1
            """, (fingerprint,))
            row = cursor.fetchone()
            
            if row:
                return {
                    "device_id": row["device_id"],
                    "fingerprint": row["fingerprint"],
                    "user_data": json.loads(row["user_data"]) if row["user_data"] else {},
                    "created_at": row["created_at"],
                    "last_seen": row["last_seen"],
                    "session_count": row["session_count"]
                }
            return None
    
    def update_user_last_seen(self, device_id: str) -> bool:
        """Update user's last_seen timestamp and increment session_count."""
        now = int(datetime.now().timestamp())
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE anonymous_users 
                SET last_seen = ?, session_count = session_count + 1
                WHERE device_id = ?
            """, (now, device_id))
            return cursor.rowcount > 0
    
    def update_user_data(self, device_id: str, user_data: Dict) -> bool:
        """Update user's data."""
        user_data_json = json.dumps(user_data)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE anonymous_users 
                SET user_data = ?
                WHERE device_id = ?
            """, (user_data_json, device_id))
            return cursor.rowcount > 0
    
    # User Preferences Operations
    
    def set_preference(self, device_id: str, key: str, value: Any) -> bool:
        """Set a user preference."""
        now = int(datetime.now().timestamp())
        value_json = json.dumps(value)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO user_preferences (device_id, key, value, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(device_id, key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
            """, (device_id, key, value_json, now))
            return cursor.rowcount > 0
    
    def get_preference(self, device_id: str, key: str) -> Optional[Any]:
        """Get a user preference."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT value FROM user_preferences 
                WHERE device_id = ? AND key = ?
            """, (device_id, key))
            row = cursor.fetchone()
            
            if row and row["value"]:
                return json.loads(row["value"])
            return None
    
    def get_all_preferences(self, device_id: str) -> Dict:
        """Get all preferences for a user."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT key, value FROM user_preferences 
                WHERE device_id = ?
            """, (device_id,))
            
            preferences = {}
            for row in cursor.fetchall():
                if row["value"]:
                    preferences[row["key"]] = json.loads(row["value"])
            return preferences
    
    def delete_preference(self, device_id: str, key: str) -> bool:
        """Delete a user preference."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM user_preferences 
                WHERE device_id = ? AND key = ?
            """, (device_id, key))
            return cursor.rowcount > 0
    
    # Analytics Operations
    
    def get_user_stats(self, days: int = 7) -> Dict:
        """Get user statistics."""
        cutoff_time = int(datetime.now().timestamp()) - (days * 86400)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Total users
            cursor.execute("SELECT COUNT(*) as count FROM anonymous_users")
            total_users = cursor.fetchone()["count"]
            
            # Active users (last 24 hours)
            cursor.execute("""
                SELECT COUNT(*) as count FROM anonymous_users 
                WHERE last_seen >= ?
            """, (int(datetime.now().timestamp()) - 86400,))
            active_today = cursor.fetchone()["count"]
            
            # New users (today)
            cursor.execute("""
                SELECT COUNT(*) as count FROM anonymous_users 
                WHERE created_at >= ?
            """, (int(datetime.now().timestamp()) - 86400,))
            new_today = cursor.fetchone()["count"]
            
            # Users within specified days
            cursor.execute("""
                SELECT COUNT(*) as count FROM anonymous_users 
                WHERE created_at >= ?
            """, (cutoff_time,))
            users_period = cursor.fetchone()["count"]
            
            return {
                "total_users": total_users,
                "active_today": active_today,
                "new_today": new_today,
                "users_last_n_days": users_period,
                "days": days
            }
    
    def cleanup_old_users(self, days: int = 30) -> int:
        """Clean up users not seen in specified days."""
        cutoff_time = int(datetime.now().timestamp()) - (days * 86400)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM anonymous_users 
                WHERE last_seen < ?
            """, (cutoff_time,))
            return cursor.rowcount


# Global database instance
_database = None


def get_database() -> Database:
    """Get the global database instance."""
    global _database
    if _database is None:
        _database = Database()
    return _database
