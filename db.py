import sqlite3
import datetime
import threading
from config import DBFILE

# Global threading lock for SQLite writes
DB_WRITE_LOCK = threading.Lock()

def init_db():
    """Initialize the logs table. Call once at app startup."""
    with DB_WRITE_LOCK:
        conn = sqlite3.connect(DBFILE, timeout=10, check_same_thread=False)
        try:
            c = conn.cursor()
            c.execute("""
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    device TEXT,
                    command TEXT,
                    result TEXT,
                    error TEXT
                )
            """)
            conn.commit()
        finally:
            conn.close()

def log_result(device_name, cmd, result, error=None):
    """
    Log every command and response, including errors, to the logs table.
    Thread-safe.
    """
    with DB_WRITE_LOCK:
        conn = sqlite3.connect(DBFILE, timeout=10, check_same_thread=False)
        try:
            c = conn.cursor()
            c.execute(
                "INSERT INTO logs (timestamp, device, command, result, error) VALUES (?, ?, ?, ?, ?)",
                (datetime.datetime.now().isoformat(), device_name, cmd, str(result), str(error) if error else None)
            )
            conn.commit()
        finally:
            conn.close()

def get_logs(limit=100):
    """
    Fetch the most recent logs for viewing/debugging.
    Thread-safe.
    """
    with DB_WRITE_LOCK:
        conn = sqlite3.connect(DBFILE, timeout=10, check_same_thread=False)
        try:
            c = conn.cursor()
            c.execute("SELECT * FROM logs ORDER BY id DESC LIMIT ?", (limit,))
            rows = c.fetchall()
            return rows
        finally:
            conn.close()
