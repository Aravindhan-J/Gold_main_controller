# db.py

import sqlite3
import datetime
from config import DBFILE

def init_db():
    """Create the logs table if it doesn't exist."""
    conn = sqlite3.connect(DBFILE)
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
    conn.close()

def log_result(device_name, cmd, result, error=None):
    """Insert a new log entry into the database."""
    conn = sqlite3.connect(DBFILE)
    c = conn.cursor()
    c.execute(
        "INSERT INTO logs (timestamp, device, command, result, error) VALUES (?, ?, ?, ?, ?)",
        (datetime.datetime.now().isoformat(), device_name, cmd, result, error)
    )
    conn.commit()
    conn.close()

def get_all_logs():
    """Fetch all logs (as a list of tuples)."""
    conn = sqlite3.connect(DBFILE)
    c = conn.cursor()
    c.execute("SELECT * FROM logs ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    return rows

def get_logs_for_device(device_name):
    """Fetch logs for a specific device."""
    conn = sqlite3.connect(DBFILE)
    c = conn.cursor()
    c.execute("SELECT * FROM logs WHERE device=? ORDER BY id DESC", (device_name,))
    rows = c.fetchall()
    conn.close()
    return rows

def delete_logs():
    """Delete all logs."""
    conn = sqlite3.connect(DBFILE)
    c = conn.cursor()
    c.execute("DELETE FROM logs")
    conn.commit()
    conn.close()

def delete_logs_for_device(device_name):
    """Delete all logs for a specific device."""
    conn = sqlite3.connect(DBFILE)
    c = conn.cursor()
    c.execute("DELETE FROM logs WHERE device=?", (device_name,))
    conn.commit()
    conn.close()

def export_logs():
    """Return all logs as a list of dicts (useful for JSON export)."""
    conn = sqlite3.connect(DBFILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM logs ORDER BY id DESC")
    rows = [dict(row) for row in c.fetchall()]
    conn.close()
    return rows

if __name__ == "__main__":
    init_db()
    print("Logs table ready.")
