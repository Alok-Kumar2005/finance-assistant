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



if __name__ == "__main__":
    init_db(db_path)