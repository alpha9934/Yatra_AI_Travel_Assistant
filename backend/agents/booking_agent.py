"""
Booking Agent
Extracts travel details, searches mock inventory, returns options.
Uses GPT-4o for complex reasoning + structured extraction.
"""
from openai import AsyncOpenAI
import json
from utils.mock_data import get_flights, get_hotels

client = AsyncOpenAI()

SYSTEM_PROMPT = """You are DIYA, a corporate travel booking assistant for Yatra.
Your job:
1. Extract travel details from the user's message (origin, destination, dates, budget, passengers)
2. Check the provided flight/hotel options
3. Recommend the best options within company policy (economy class for <4hr flights, budget hotel <₹6000/night)
4. Respond in a friendly, concise way with clear options

Company policy reminders:
- Flights: Economy only unless >6 hours
- Hotels: Max ₹6000/night for Tier-1 cities, ₹4000 for others
- Advance booking required: at least 3 days before travel

Always respond in JSON:
{
  "message": "<friendly response to user>",
  "extracted": {"origin": "", "destination": "", "departure": "", "return": "", "passengers": 1, "trip_type": "one-way|round-trip"},
  "flights": [<list of recommended flights from provided data>],
  "hotels": [<list of recommended hotels from provided data>],
  "policy_flags": [<any policy violations to highlight>]
}
"""

async def handle_booking(user_message: str, history: list = []) -> dict:
    flights = get_flights()
    hotels = get_hotels()

    context = f"""
Available Flights: {json.dumps(flights, indent=2)}
Available Hotels: {json.dumps(hotels, indent=2)}
User request: {user_message}
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
