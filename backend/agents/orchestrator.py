"""
Orchestrator Agent
Classifies user intent and routes to the correct sub-agent.
Uses GPT-4o-mini (cheap) since it's just classification + routing.
"""
from openai import AsyncOpenAI
import json

client = AsyncOpenAI()

SYSTEM_PROMPT = """You are the orchestrator for a corporate travel assistant.
Classify the user's message into one of these intents:

- "booking": wants to search, find, or book flights or hotels
- "expense": wants to log, add, record, scan, or submit an expense, receipt, bill, or any travel cost. Examples: "log expense", "add expense", "I spent", "cab cost", "record a bill", "Ola cab ₹680", "₹500 meal"
- "policy": asking about company travel rules, policy, limits, approval, or reimbursement eligibility
- "disruption": reporting or asking about a flight delay, cancellation, missed flight, or rebooking
- "general": greetings or anything that doesn't fit above

IMPORTANT: When any rupee amount (₹, Rs, INR) OR words like "log", "add", "spent", "paid", "cab", "meal", "receipt" appear — classify as "expense".

Respond ONLY with valid JSON:
{"intent": "<intent>", "summary": "<one sentence summary of request>", "confidence": 0.0-1.0}
"""

async def classify_intent(user_message: str, history: list = []) -> dict:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for h in history[-4:]:
        messages.append(h)
    messages.append({"role": "user", "content": user_message})

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)