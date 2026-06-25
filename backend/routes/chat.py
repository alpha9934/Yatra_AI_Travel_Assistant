from fastapi import APIRouter
from pydantic import BaseModel
from agents.orchestrator import classify_intent
from agents.booking_agent import handle_booking
from agents.policy_agent import check_policy
from agents.disruption_agent import handle_disruption
from agents.expense_agent import parse_receipt_text

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    history: list = []

@router.post("/")
async def chat(req: ChatRequest):
    classification = await classify_intent(req.message, req.history)
    intent = classification.get("intent", "general")

    if intent == "booking":
        data = await handle_booking(req.message, req.history)
        return {"intent": intent, "classification": classification, "data": data}

    elif intent == "expense":
        data = await parse_receipt_text(req.message)
        data["message"] = f"Got it! Logged ₹{data.get('total_amount', '')} at {data.get('merchant', 'unknown')}. {'✓ Reimbursable' if data.get('reimbursable') else '✗ Not reimbursable under policy'}."
        return {"intent": intent, "classification": classification, "data": data}

    elif intent == "policy":
        data = await check_policy(req.message, req.history)
        return {"intent": intent, "classification": classification, "data": data}

    elif intent == "disruption":
        data = await handle_disruption(req.message, req.history)
        return {"intent": intent, "classification": classification, "data": data}

    else:
        return {
            "intent": "general",
            "classification": classification,
            "data": {
                "message": "Hi! I'm DIYA, your Yatra travel assistant. I can help you:\n• Search and book flights & hotels\n• Scan and log expense receipts\n• Answer company travel policy questions\n• Handle flight disruptions and rebooking\n\nWhat do you need today?",
            }
        }