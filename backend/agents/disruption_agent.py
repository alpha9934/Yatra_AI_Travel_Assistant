"""
Disruption Agent
Handles flight delays, cancellations, and proactive rebooking suggestions.
Uses GPT-4o for reasoning about alternatives.
"""
from openai import AsyncOpenAI
import json
from utils.mock_data import get_flights
from datetime import datetime

client = AsyncOpenAI()

SYSTEM_PROMPT = """You are a proactive travel disruption assistant for Yatra.
When a traveler reports a flight delay or cancellation:
1. Acknowledge the disruption empathetically
2. Find the best alternative options from the available flights
3. Consider: next available flight, travel time, cost difference
4. Check if hotel rebooking is needed
5. Remind about meal voucher entitlements for delays > 2 hours

For delays > 2 hours: Traveler is entitled to meal voucher (up to ₹400)
For cancellations: Full refund or next available flight (airline's obligation)

Respond in JSON:
{
  "message": "<empathetic, action-oriented response>",
  "disruption_type": "delay|cancellation|missed|other",
  "original_flight": {"flight_no": "", "route": "", "original_time": ""},
  "alternatives": [<list of alternative flights from provided data>],
  "entitlements": ["<what traveler is entitled to>"],
  "hotel_rebooking_needed": true|false,
  "escalate_to_support": true|false,
  "action_items": ["<list of immediate action items for traveler>"]
}
"""

async def handle_disruption(user_message: str, history: list = []) -> dict:
    flights = get_flights()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    context = f"""
Current time: {now}
Available alternative flights: {json.dumps(flights, indent=2)}
Traveler's message: {user_message}
"""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for h in history[-6:]:
        messages.append(h)
    messages.append({"role": "user", "content": context})

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.3,
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)
