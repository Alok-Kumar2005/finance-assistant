# finance-assistant


# AI Engineer Assignment 

## 1. Memory

After Session 1, I stored only durable information that would still matter in future conversations. This included the user’s ₹30,000 house-fund commitment, the food delivery reduction goal, the actual food delivery spending amount, the reminder details, and a short summary of the user’s concern.

I deliberately did not store temporary financial data like current account balance, upcoming bills, or transaction lists. Those values can change between sessions, so I treated them as live data that should always come from tools instead of memory. My goal was to keep memory focused on long-term intent and commitments rather than stale numbers.

---

## 2. Tools vs. LLM

One decision I gave to the LLM was determining how to respond conversationally to the user’s purchase question in Session 2. The LLM handled the judgment part: connecting the MacBook purchase with the user’s previously stated savings goal and deciding how cautious the recommendation should sound.

One decision I kept in code was memory persistence and tool execution. SQLite storage, memory reads/writes, and tool dispatching are deterministic tasks, so I implemented them directly in Python instead of relying on the LLM. I also avoided using the LLM for arithmetic or data retrieval because those are more reliable when handled programmatically.

---

## 3. AI Usage

I used AI tools mainly for brainstorming prompt structures, reviewing edge cases, and improving code organization. For example, AI helped me refine the memory extraction prompt and suggested a cleaner structure for the agent loop.

One suggestion I rejected was storing the full conversation history as memory. I felt that would make retrieval noisy and blur the distinction between memory and context. Instead, I chose to store only structured, durable facts that were actually useful across sessions.

---

## 4. If I Had One More Week

If I had another week, I would redesign the memory system. Right now, memory is stored as simple key-value pairs in SQLite, which works for this assignment but does not scale well for longer user histories.

I would move toward a layered memory design:

* short-term conversational memory,
* long-term user preferences/goals,
* and event-based financial memories.

I would also add memory scoring or retrieval ranking so the agent could decide which memories are most relevant to the current conversation instead of loading everything every time.




(finance-assistant) C:\Users\Lenovo\Work\finance-assistant>python agents.py 1
  SESSION 1  —  2025-11-03

User: I just got my salary credited. Help me figure out how much I can realistically save this month.

Assistant: You have ₹128,000 in your checking account. Your upcoming bills total ₹46,500. Considering your income and expenses, you can realistically save ₹73,500 this month.

------------------------------------------------------------

User: I feel like I'm spending too much on food delivery. How much did I actually spend on it last month?

Assistant: You spent ₹8,650 on food delivery last month.

------------------------------------------------------------

User: Okay that's worse than I thought. Let's say I want to cut that in half AND put aside ₹30,000 for my house fund this month — is that realistic given my upcoming bills?

Assistant: You want to cut your food delivery spend in half to ₹4,325 and save ₹30,000 for your house fund. Your upcoming bills total ₹46,500. You have ₹128,000 in your checking account. 

Considering your goals and bills, you can realistically save ₹30,000 for your house fund and cut your food delivery spend. You will be left with ₹47,175 for other expenses.

------------------------------------------------------------

User: Got it. Remind me to actually transfer the ₹30,000 to my house fund on the 25th.

Assistant: I've set a reminder for you to transfer ₹30,000 to your house fund on 2025-11-25.

------------------------------------------------------------

[POST-SESSION 1] Extracting memory facts...

  [MEM WRITE] savings_plan_house_fund_inr = 30000
  [MEM WRITE] savings_plan_food_cut_target = "cut food delivery spend in half to \u20b94,325"
  [MEM WRITE] food_delivery_spend_oct_inr = 8650
  [MEM WRITE] reminder_date = "2025-11-25"
  [MEM WRITE] reminder_content = "transfer \u20b930,000 to house fund"
  [MEM WRITE] user_concern = "spending too much on food delivery and saving for house fund"

  [MEMORY] Persisted 6 facts from Session 1 to SQLite.


(finance-assistant) C:\Users\Lenovo\Work\finance-assistant>python agents.py 2
  SESSION 2  —  2025-11-06

User: Hey, my colleague is selling his MacBook for ₹80,000, barely used. I've been wanting to upgrade. Should I buy it?

Assistant: You have ₹128,000 in your checking account. Your upcoming bills include rent (₹25,000 on Nov 5), mutual funds SIP (₹10,000 on Nov 10), internet and mobile (₹3,500 on Nov 15), and credit card (₹8,000 on Nov 20). 

Considering your current balance and upcoming bills, you can afford the ₹80,000 MacBook. However, you might want to ensure you have enough for the upcoming bills and other expenses.

------------------------------------------------------------
