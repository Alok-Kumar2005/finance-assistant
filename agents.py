from tools import *
import json
import sys
import textwrap
from datetime import datetime
import sqlite3
import os
from groq import Groq
from dotenv import load_dotenv

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

groq_client = Groq(
    api_key=os.environ.get("GROQ_API_KEY")
)

def call_llm( messages: list[dict], system_message: str | None = None, tools: list[dict] | None = None, 
             max_tokens: int = 1024, temperature: float = 0.2, tool_choice: str = "auto",):
    req_messages = []
    if system_message:
        req_messages.append({"role": "system", "content": system_message})
    req_messages.extend(messages)
 
    payload = {
        "model": model,
        "messages": req_messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
 
    if tools:
        payload["tools"] = [{"type": "function", "function": t} for t in TOOL_SCHEMAS]
        payload["tool_choice"] = tool_choice
 
    return groq_client.chat.completions.create(**payload)


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
        "parameters": {                          # <-- was "input_schema", must be "parameters" for Groq
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "How many days back to look"}
            },
            "required": ["days"],
        },
        "strict": False,  # <-- allow extra fields in the tool call (e.g. "reason") without causing an error
    },
    {
        "name": "get_account_balance",
        "description": (
            "Get current account balances. Always call this when the user asks about "
            "what they can afford — balances change between sessions."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
        },
        "strict": False,
    },
    {
        "name": "get_upcoming_bills",
        "description": "Get scheduled bills/payments due in the next N days.",
        "parameters": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Look-ahead window in days"}
            },
            "required": ["days"],
        },
        "strict": False,
    },
    {
        "name": "set_reminder",
        "description": "Set a reminder for the user. Always call this when they ask to be reminded of something.",
        "parameters": {
            "type": "object",
            "properties": {
                "date":    {"type": "string", "description": "Date in YYYY-MM-DD format"},
                "content": {"type": "string", "description": "Reminder text"},
            },
            "required": ["date", "content"],
        },
        "strict": False,
    },
]

## call tool fucntion and return a json string
def dispatch_tool(name: str, tool_input: dict) -> str:
    if name == "get_recent_transactions":
        result = get_recent_transactions(int(tool_input["days"]))  ## error
    elif name == "get_account_balance":
        result = get_account_balance()
    elif name == "get_upcoming_bills":
        result = get_upcoming_bills(tool_input.get("days", 30))
    elif name == "set_reminder":
        result = set_reminder(tool_input["date"], tool_input["content"])
    else:
        result = {"error": f"Unknown tool: {name}"}
    return json.dumps(result)

## extract and store the facts in memory after conversation
def extract_and_store_sess1(conn, conversation: list[dict]):
 
    prompt = textwrap.dedent(f"""
        You are a memory extractor for a finance assistant.
        Below is a conversation from Session 1 (Monday, Nov 3, 2025).
        Extract ONLY durable facts that would still matter three days later.
        
        Return a JSON object with exactly these keys (omit a key if unknown):
          savings_plan_house_fund_inr   : integer  — amount user committed to transfer to house fund
          savings_plan_food_cut_target  : string   — description of food delivery reduction goal
          food_delivery_spend_oct_inr   : integer  — actual October food delivery spend from transaction data
          reminder_date                 : string   — YYYY-MM-DD of the reminder the user set
          reminder_content              : string   — what the reminder says
          user_concern                  : string   — one-sentence summary of user's main concern this session
 
        Return ONLY the JSON object. No markdown, no explanation.
 
        CONVERSATION:
        {json.dumps(conversation, ensure_ascii=False, indent=2)}
    """).strip()

    response = call_llm(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=400,
    )
    raw = response.choices[0].message.content.strip()
 
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
 
    try:
        facts = json.loads(raw)
    except json.JSONDecodeError:
        print(f"  [WARN] Could not parse memory JSON, storing raw: {raw[:100]}")
        facts = {"raw_extraction": raw}
 
    for key, value in facts.items():
        write_memory(conn, key, value, source="session1")
 
    print(f"\n  [MEMORY] Persisted {len(facts)} facts from Session 1 to SQLite.\n")


def build_system_prompt(session: int, conn) -> str:
    today = session_date[session] 
    base = textwrap.dedent(f"""
        You are a personal finance companion for {user_profile['name']}, age {user_profile['age']}, 
        living in {user_profile['city']}. Today is {today}.
 
        User profile:
          Monthly income (post-tax): ₹{user_profile['monthly_income_inr']:,} — credited on the 1st
          Long-term goal: {user_profile['stated_goal']}
 
        Principles:
        - Be direct and specific — use actual numbers, not vague advice.
        - Always call tools for live data (balances, bills, transactions). Never cite stale numbers from memory.
        - Use memory for durable facts: commitments, goals, reminders.
        - When the user asks about affordability, check balance AND upcoming bills via tools.
        - Set reminders via tool when the user requests them or when it's clearly appropriate.
        - Keep responses concise — 3–5 sentences max unless showing a breakdown.
    """).strip()
 
    if session == 2:
        mem = read_all_memory(conn)
        if mem:
            mem_block = json.dumps(mem, ensure_ascii=False, indent=2)
            base += f"""
 
--- MEMORY FROM SESSION 1 (Monday, Nov 3) ---
{mem_block}
--- END MEMORY ---
 
Important: The user has NOT mentioned any of this yet in today's session. 
Use this context proactively but naturally — connect new questions to known plans.
For any financial figures (balance, bills), call the tools — do NOT quote Monday's numbers."""
 
    return base


def run_agent(system: str, messages: list[dict]) -> tuple[str, list[dict]]:
    while True:
        response = call_llm(
            messages=messages,
            system_message=system,
            tools=TOOL_SCHEMAS,
        )
 
        msg = response.choices[0].message
        finish_reason = response.choices[0].finish_reason
 
        if finish_reason == "tool_calls":
            assistant_msg = {
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id":       tc.id,
                        "type":     "function",
                        "function": {
                            "name":      tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ],
            }
            messages = messages + [assistant_msg]
 
            # dispatch each tool call and append results as tool messages before the next LLM response
            for tc in msg.tool_calls:
                tool_name = tc.function.name
                try:
                    tool_input = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    tool_input = {}
 
                result_str = dispatch_tool(tool_name, tool_input)
 
                ### tool result appended
                messages = messages + [{
                    "role":         "tool",
                    "tool_call_id": tc.id,
                    "name":         tool_name,
                    "content":      result_str,
                }]
        else:
            # finish_reason == "stop" — final text response
            final_text = (msg.content or "").strip()
            messages = messages + [{"role": "assistant", "content": final_text}]
            return final_text, messages
 

def run_session(session: int, user_turns: list[str]):
    conn = init_db(db_path)
    print(f"  SESSION {session}  —  {session_date[session]}")
 
    system = build_system_prompt(session, conn)
    messages = load_session_messages(conn, session)
 
    for user_text in user_turns:
        print(f"\nUser: {user_text}")
        save_message(conn, session, "user", user_text)
        if not messages or messages[-1].get("content") != user_text:
            messages = messages + [{"role": "user", "content": user_text}]
 
        assistant_text, messages = run_agent(system, messages)
 
        print(f"\nAssistant: {assistant_text}\n")
        save_message(conn, session, "assistant", assistant_text)
        print("-" * 60)
 
    # after the end of the session, extract durable facts from the conversation and store in memory for next session
    if session == 1:
        print("\n[POST-SESSION 1] Extracting memory facts...\n")
        full_convo = load_session_messages(conn, session=1)
        extract_and_store_sess1(conn, full_convo)
 
    conn.close()


SESSION_1_TURNS = [
    "I just got my salary credited. Help me figure out how much I can realistically save this month.",
    "I feel like I'm spending too much on food delivery. How much did I actually spend on it last month?",
    "Okay that's worse than I thought. Let's say I want to cut that in half AND put aside ₹30,000 for my house fund this month — is that realistic given my upcoming bills?",
    "Got it. Remind me to actually transfer the ₹30,000 to my house fund on the 25th.",
]
 
SESSION_2_TURNS = [
    "Hey, my colleague is selling his MacBook for ₹80,000, barely used. I've been wanting to upgrade. Should I buy it?",
]

if __name__ == "__main__":
    # init_db(db_path)
    # print(dispatch_tool("get_upcoming_bills", {"days": 30}))

    session = int(sys.argv[1]) if len(sys.argv) > 1 else 1
 
    if session == 1:
        run_session(1, SESSION_1_TURNS)
    elif session == 2:
        run_session(2, SESSION_2_TURNS)
    else:
        print("Usage: python agent_groq.py 1   (or 2)")
        sys.exit(1)
 