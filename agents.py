from tools import *
import json
import sys
import textwrap
from datetime import datetime
import sqlite3
import groq


## configs
db_path = "memory.db"
model = "meta-llama/llama-4-scout-17b-16e-instruct"
session_date = {1: "2025-11-03", 2: "2025-11-06"}
user_profile = {
    "name": "Priya Sharma",
    "age": 28,
    "city": "Bangalore",
    "monthly_income_inr": 120000,
    "stated_goal": "Save ₹15 lakh in 2 years for a house down payment in Bangalore",
}


## database creation
## idea: 2 tables
## first one holds all the message between user and assistant
## second one hold important facts stored from sessions

def init_db(dp_path: str)->sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            ts TEXT DEFAULT (datetime('now'))
        );
 
        CREATE TABLE IF NOT EXISTS memory (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL, 
            source TEXT,
            ts TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    return conn

def save_message(conn, session: int, role: str, content: str):
    conn.execute(
        "INSERT INTO messages (session, role, content) VALUES (?, ?, ?)",
        (session, role, content),
    )
    conn.commit()
 
 
def load_session_messages(conn, session: int) -> list[dict]:
    rows = conn.execute(
        "SELECT role, content FROM messages WHERE session = ? ORDER BY id",
        (session,),
    ).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in rows]
 
 
def write_memory(conn, key: str, value, source: str):
    conn.execute(
        """INSERT INTO memory (key, value, source)
           VALUES (?, ?, ?)
           ON CONFLICT(key) DO UPDATE SET value=excluded.value,
                                          source=excluded.source,
                                          ts=datetime('now')""",
        (key, json.dumps(value), source),
    )
    conn.commit()
    print(f"  [MEM WRITE] {key} = {json.dumps(value)[:120]}")
 
 
def read_memory(conn, key: str):
    row = conn.execute("SELECT value FROM memory WHERE key = ?", (key,)).fetchone()
    if row:
        val = json.loads(row["value"])
        print(f"  [MEM READ]  {key} = {json.dumps(val)[:120]}")
        return val
    return None
 
 
def read_all_memory(conn) -> dict:
    rows = conn.execute("SELECT key, value FROM memory").fetchall()
    return {r["key"]: json.loads(r["value"]) for r in rows}
 
TOOL_SCHEMAS = [
    {
        "name": "get_recent_transactions",
        "description": (
            "Fetch transactions from the last N days. "
            "Use this to answer questions about spending — never quote stale memory for live figures."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "How many days back to look"}
            },
            "required": ["days"],
        },
    },
    {
        "name": "get_account_balance",
        "description": (
            "Get current account balances. Always call this when the user asks about "
            "what they can afford — balances change between sessions."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_upcoming_bills",
        "description": "Get scheduled bills/payments due in the next N days.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Look-ahead window in days"}
            },
            "required": ["days"],
        },
    },
    {
        "name": "set_reminder",
        "description": "Set a reminder for the user. Always call this when they ask to be reminded of something.",
        "input_schema": {
            "type": "object",
            "properties": {
                "date":    {"type": "string", "description": "Date in YYYY-MM-DD format"},
                "content": {"type": "string", "description": "Reminder text"},
            },
            "required": ["date", "content"],
        },
    },
]

## call tool fucntion and return a json string
def dispatch_tool(name: str, tool_input: dict) -> str:
    if name == "get_recent_transactions":
        result = get_recent_transactions(tool_input["days"])
    elif name == "get_account_balance":
        result = get_account_balance()
    elif name == "get_upcoming_bills":
        result = get_upcoming_bills(tool_input.get("days", 30))
    elif name == "set_reminder":
        result = set_reminder(tool_input["date"], tool_input["content"])
    else:
        result = {"error": f"Unknown tool: {name}"}
    return json.dumps(result)


if __name__ == "__main__":
    # init_db(db_path)
    # print(dispatch_tool("get_upcoming_bills", {"days": 30}))
    pass