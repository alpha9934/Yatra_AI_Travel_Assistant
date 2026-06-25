"""
Expense / RECAP Agent
Parses receipt images or text descriptions into structured expense records.
Uses GPT-4o vision for images, GPT-4o-mini for text-only.
"""
from openai import AsyncOpenAI
import json, base64

client = AsyncOpenAI()

SYSTEM_PROMPT = """You are RECAP, a corporate expense processing assistant for Yatra.
Extract expense information from the receipt/description provided.

Company reimbursement policy:
- Meals: Max ₹800/meal (₹1200 for client entertainment)
- Taxi/Cab: Reimbursable with receipt
- Alcohol: NOT reimbursable — flag if detected
- Personal items: NOT reimbursable
- GST/Tax: Always extract separately

Respond ONLY in JSON:
{
  "merchant": "<name>",
  "date": "<YYYY-MM-DD>",
  "total_amount": 0.0,
  "tax_amount": 0.0,
  "net_amount": 0.0,
  "category": "meals|transport|accommodation|other",
  "line_items": [{"description": "", "amount": 0.0}],
  "reimbursable": true|false,
  "policy_flags": ["<any violations>"],
  "confidence": 0.0-1.0,
  "notes": "<any additional notes>"
}
"""

async def parse_receipt_text(description: str) -> dict:
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Parse this expense: {description}"},
        ],
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


async def parse_receipt_image(image_base64: str, mime_type: str = "image/jpeg") -> dict:
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{image_base64}",
                            "detail": "high",
                        },
                    },
                    {"type": "text", "text": "Extract all expense details from this receipt."},
                ],
            },
        ],
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)
