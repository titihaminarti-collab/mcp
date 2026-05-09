# mcp_project/utils/db.py
import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

DB_PATH = Path("data/conversations.db")

def init_db():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            history TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_history(session_id: str, history: List[Dict[str, str]]):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO sessions (session_id, history, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
        (session_id, json.dumps(history, ensure_ascii=False))
    )
    conn.commit()
    conn.close()

def load_history(session_id: str) -> List[Dict[str, str]]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT history FROM sessions WHERE session_id = ?", (session_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return json.loads(row[0])
    return []

def get_or_create_session(session_id: str) -> List[Dict[str, str]]:
    init_db()
    return load_history(session_id)