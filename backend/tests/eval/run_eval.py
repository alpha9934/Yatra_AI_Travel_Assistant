"""
Eval Suite — Golden Test Cases
Tests routing accuracy, policy RAG quality, and expense parsing.

Usage:
    python tests/eval/run_eval.py

Outputs a summary table with pass/fail per test case.
"""
import asyncio
import os
import sys
import json
import time
import logging
from dataclasses import dataclass, field

# Suppress non-critical warnings during eval
logging.disable(logging.WARNING)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from dotenv import load_dotenv
load_dotenv()

from agents.orchestrator import classify_intent
from agents.policy_agent import check_policy
from agents.expense_agent import parse_receipt_text

# Safe audit log import — non-fatal if supabase not available in eval context
try:
    from db.audit_repo import log_event
except ImportError:
    def log_event(*args, **kwargs): pass


# ─── Data Types ──────────────────────────────────────────────────────────────

@dataclass
class EvalCase:
    id:               str
    category:         str
    input:            str
    expected_intent:  str | None = None
    expected_allowed: bool | None = None
    expected_fields:  dict = field(default_factory=dict)
    min_confidence:   float = 0.7


@dataclass
class EvalResult:
    case_id:    str
    category:   str
    passed:     bool
    score:      float
    latency_ms: int
    details:    dict


# ─── Golden Test Cases ────────────────────────────────────────────────────────

ROUTING_CASES = [
    EvalCase("R01", "routing", "Book me a flight from Bangalore to Delhi next Monday", expected_intent="booking"),
    EvalCase("R02", "routing", "Find me a hotel in Mumbai for 3 nights", expected_intent="booking"),
    EvalCase("R03", "routing", "Log ₹680 Ola cab to airport", expected_intent="expense"),
    EvalCase("R04", "routing", "I spent ₹340 at Café Coffee Day", expected_intent="expense"),
    EvalCase("R05", "routing", "Can I claim alcohol in client dinner?", expected_intent="policy"),
    EvalCase("R06", "routing", "What's the hotel limit for Tier-2 cities?", expected_intent="policy"),
    EvalCase("R07", "routing", "My flight 6E-204 is delayed by 3 hours", expected_intent="disruption"),
    EvalCase("R08", "routing", "IndiGo cancelled my flight to Delhi", expected_intent="disruption"),
    EvalCase("R09", "routing", "Hello, what can you help me with?", expected_intent="general"),
    EvalCase("R10", "routing", "Add expense: ₹1200 team lunch at Mainland China", expected_intent="expense"),
    EvalCase("R11", "routing", "Do I need approval for a ₹45,000 trip?", expected_intent="policy"),
    EvalCase("R12", "routing", "I missed my connecting flight", expected_intent="disruption"),
]

POLICY_CASES = [
    EvalCase("P01", "policy", "Can I fly business class on a 3-hour domestic flight?",
             expected_allowed=False),
    EvalCase("P02", "policy", "Is alcohol reimbursable in client entertainment?",
             expected_allowed=False),
    EvalCase("P03", "policy", "What is the hotel limit in Bengaluru?",
             expected_fields={"answer": "6000"}),
    EvalCase("P04", "policy", "How many days in advance do I need to book a flight?",
             expected_fields={"answer": "3"}),
    EvalCase("P05", "policy", "My trip cost is ₹40,000. Do I need manager approval?",
             expected_allowed=True, expected_fields={"approval_needed": True}),
    EvalCase("P06", "policy", "Can I keep hotel loyalty points for myself?",
             expected_allowed=True),
    EvalCase("P07", "policy", "What meal allowance do I get for international travel?",
             expected_fields={"answer": "1500"}),
    EvalCase("P08", "policy", "Within how many days must I submit expenses?",
             expected_fields={"answer": "30"}),
]

EXPENSE_CASES = [
    EvalCase("E01", "expense", "Ola cab ₹680 from airport to office on Jan 10",
             expected_fields={"total_amount": 680, "category": "transport", "reimbursable": True}),
    EvalCase("E02", "expense", "Team dinner at Punjab Grill ₹4500 for 3 people",
             expected_fields={"category": "meals", "total_amount": 4500}),
    EvalCase("E03", "expense", "Whiskey and beer at hotel bar ₹1200",
             expected_fields={"reimbursable": False}),
    EvalCase("E04", "expense", "ITC hotel stay 2 nights ₹12000",
             expected_fields={"category": "accommodation", "total_amount": 12000}),
    EvalCase("E05", "expense", "Personal grocery shopping ₹800",
             expected_fields={"reimbursable": False}),
]


# ─── Evaluators ──────────────────────────────────────────────────────────────

async def eval_routing(case: EvalCase) -> EvalResult:
    start = time.time()
    result = await classify_intent(case.input)
    latency = int((time.time() - start) * 1000)

    actual_intent = result.get("intent")
    confidence    = result.get("confidence", 0)
    passed        = (actual_intent == case.expected_intent) and (confidence >= case.min_confidence)

    return EvalResult(
        case_id=case.id, category=case.category, passed=passed,
        score=1.0 if passed else 0.0, latency_ms=latency,
        details={"expected": case.expected_intent, "actual": actual_intent, "confidence": confidence},
    )


async def eval_policy(case: EvalCase) -> EvalResult:
    start = time.time()
    result = await check_policy(case.input)
    latency = int((time.time() - start) * 1000)

    checks = []
    if case.expected_allowed is not None:
        checks.append(result.get("allowed") == case.expected_allowed)
    for key, expected_val in case.expected_fields.items():
        actual = result.get(key)
        if isinstance(expected_val, str):
            checks.append(str(expected_val) in str(actual))
        elif isinstance(expected_val, bool):
            checks.append(actual == expected_val)
        else:
            checks.append(actual == expected_val)

    passed = all(checks) if checks else True
    score  = sum(checks) / len(checks) if checks else 1.0

    return EvalResult(
        case_id=case.id, category=case.category, passed=passed,
        score=score, latency_ms=latency,
        details={"answer": result.get("answer", "")[:100], "allowed": result.get("allowed"), "flags": case.expected_fields},
    )


async def eval_expense(case: EvalCase) -> EvalResult:
    start = time.time()
    result = await parse_receipt_text(case.input)
    latency = int((time.time() - start) * 1000)

    checks = []
    for key, expected_val in case.expected_fields.items():
        actual = result.get(key)
        if isinstance(expected_val, bool):
            checks.append(actual == expected_val)
        elif isinstance(expected_val, (int, float)):
            checks.append(abs(float(actual or 0) - float(expected_val)) < 1.0)
        else:
            checks.append(str(actual) == str(expected_val))

    passed = all(checks) if checks else True
    score  = sum(checks) / len(checks) if checks else 1.0

    return EvalResult(
        case_id=case.id, category=case.category, passed=passed,
        score=score, latency_ms=latency,
        details={"merchant": result.get("merchant"), "amount": result.get("total_amount"),
                 "category": result.get("category"), "reimbursable": result.get("reimbursable")},
    )


# ─── Runner ──────────────────────────────────────────────────────────────────

async def run_all_evals() -> None:
    print("\n" + "="*70)
    print("  YATRA AI EVAL SUITE")
    print("="*70)

    all_results: list[EvalResult] = []

    # Routing
    print("\n[ROUTING] Intent Classification")
    for case in ROUTING_CASES:
        r = await eval_routing(case)
        all_results.append(r)
        status = "✓ PASS" if r.passed else "✗ FAIL"
        print(f"  {r.case_id} {status:8} {r.latency_ms:4}ms | {case.input[:50]}")
        if not r.passed:
            print(f"           expected={r.details['expected']} actual={r.details['actual']} conf={r.details['confidence']:.2f}")

    # Policy
    print("\n[POLICY] RAG Policy Q&A")
    for case in POLICY_CASES:
        r = await eval_policy(case)
        all_results.append(r)
        status = "✓ PASS" if r.passed else "✗ FAIL"
        print(f"  {r.case_id} {status:8} {r.latency_ms:4}ms | {case.input[:50]}")
        if not r.passed:
            print(f"           details={json.dumps(r.details, ensure_ascii=False)[:120]}")

    # Expense
    print("\n[EXPENSE] Receipt Parsing")
    for case in EXPENSE_CASES:
        r = await eval_expense(case)
        all_results.append(r)
        status = "✓ PASS" if r.passed else "✗ FAIL"
        print(f"  {r.case_id} {status:8} {r.latency_ms:4}ms | {case.input[:50]}")
        if not r.passed:
            print(f"           details={r.details}")

    # Summary
    total       = len(all_results)
    passed      = sum(1 for r in all_results if r.passed)
    avg_latency = sum(r.latency_ms for r in all_results) // total

    print("\n" + "="*70)
    print(f"  RESULTS: {passed}/{total} passed ({passed/total*100:.0f}%)")
    print(f"  AVG LATENCY: {avg_latency}ms")

    by_cat: dict[str, list[EvalResult]] = {}
    for r in all_results:
        by_cat.setdefault(r.category, []).append(r)
    for cat, results in by_cat.items():
        cat_pass = sum(1 for r in results if r.passed)
        print(f"  {cat.upper():10}: {cat_pass}/{len(results)}")
    print("="*70 + "\n")

    # Exit with error code if not 100%
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    asyncio.run(run_all_evals())