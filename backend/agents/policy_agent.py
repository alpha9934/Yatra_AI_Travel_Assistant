"""
Policy Agent — RAG-powered
Answers corporate travel policy questions using Pinecone retrieval + GPT-4o-mini.
Falls back to static policy if RAG is unavailable (e.g. no Pinecone key set).
"""
import os
import json
import logging
from utils.llm_client import chat_completion

logger = logging.getLogger(__name__)

USE_RAG = bool(os.environ.get("PINECONE_API_KEY", ""))


async def check_policy(question: str, history: list = []) -> dict:
    if USE_RAG:
        logger.info("policy_agent using RAG pipeline")
        from rag.pipeline import rag_policy_answer
        return await rag_policy_answer(question, history)
    else:
        logger.info("policy_agent using static fallback (no PINECONE_API_KEY)")
        return await _static_policy_answer(question, history)


# ─── Static Fallback (kept for local dev without Pinecone) ───────────────────

COMPANY_POLICY = """
YATRA CORPORATE TRAVEL POLICY (v2.1 — FY2025)

FLIGHTS:
- Economy class for all domestic flights
- Business class allowed for flights > 6 hours or C-suite employees
- Book at least 3 business days in advance (exceptions need manager approval)
- Preferred airline: Air India, IndiGo, Vistara (in that order)
- Max fare deviation from lowest available: 20%

HOTELS:
- Tier-1 cities (Mumbai, Delhi, Bengaluru, Hyderabad): Max ₹6,000/night
- Tier-2 cities: Max ₹4,000/night
- Preferred chains: Marriott, ITC, Taj (business rate applies)
- Loyalty points can be retained personally

MEALS & DAILY ALLOWANCE:
- Daily meal allowance: ₹800/day (domestic), ₹1,500/day (international)
- Client entertainment: Max ₹1,200/person, requires pre-approval > 5 people
- Alcohol is NOT reimbursable under any circumstances

GROUND TRANSPORT:
- Uber/Ola cabs: Reimbursable with receipt
- Auto-rickshaw: Reimbursable up to ₹200
- Personal vehicle: ₹8/km (submit odometer reading)
- Airport pickup/drop: Reimbursable

APPROVALS:
- Trips < ₹15,000 total: Self-approved
- Trips ₹15,000–₹50,000: Reporting manager approval
- Trips > ₹50,000: Department head approval
- International travel: Always requires Department head + HR approval

EXPENSE SUBMISSION:
- Submit within 30 days of trip completion
- All expenses > ₹500 require original receipt
- Use the Yatra Expense Portal
"""

STATIC_SYSTEM_PROMPT = f"""You are a corporate travel policy assistant for Yatra.
Answer questions about company travel policy clearly and helpfully.

{COMPANY_POLICY}

Respond in JSON:
{{
  "answer": "<clear, direct answer>",
  "allowed": true|false|null,
  "relevant_policy": "<quote the exact policy clause>",
  "suggestion": "<alternative if not allowed, or tip>",
  "approval_needed": true|false,
  "sources": ["travel_policy_v2.1.md"],
  "retrieval_confidence": 0.85
}}
"""


async def _static_policy_answer(question: str, history: list = []) -> dict:
    messages = [{"role": "system", "content": STATIC_SYSTEM_PROMPT}]
    for h in history[-4:]:
        messages.append(h)
    messages.append({"role": "user", "content": question})

    content = await chat_completion(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.1,
        response_format={"type": "json_object"},
        caller="policy_agent_static",
    )
    return json.loads(content)
