#!/usr/bin/env python3
"""
Local Setup Verification Script
================================
Run this BEFORE starting the app to verify all external services are reachable.

Usage:
    cd backend
    python test_connections.py

Checks:
  ✅ OpenAI API key is valid
  ✅ Supabase connection + tables exist
  ✅ Pinecone connection + index exists
  ✅ All required env vars are present
"""

import os
import sys

from dotenv import load_dotenv
load_dotenv()

# ── Colour helpers ─────────────────────────────────────────────
OK   = "\033[92m✅\033[0m"
FAIL = "\033[91m❌\033[0m"
WARN = "\033[93m⚠️ \033[0m"
INFO = "\033[94mℹ️ \033[0m"

results = []

def check(label: str, passed: bool, detail: str = ""):
    icon = OK if passed else FAIL
    msg = f"  {icon}  {label}"
    if detail:
        msg += f"\n        {detail}"
    print(msg)
    results.append(passed)
    return passed


# ── 1. ENV VARS ────────────────────────────────────────────────
print("\n📋  Checking environment variables…")

required_vars = {
    "OPENAI_API_KEY":       "OpenAI API key",
    "SUPABASE_URL":         "Supabase project URL",
    "SUPABASE_SERVICE_KEY": "Supabase secret key (sb_secret_...)",
    "PINECONE_API_KEY":     "Pinecone API key",
    "PINECONE_INDEX":       "Pinecone index name",
}

optional_vars = {
    "API_KEYS":        "API auth keys (leave blank for open dev)",
    "PINECONE_CLOUD":  "Pinecone cloud provider (default: aws)",
    "PINECONE_REGION": "Pinecone region (default: us-east-1)",
    "ALLOWED_ORIGINS": "CORS origins",
    "LOG_LEVEL":       "Log verbosity",
}

all_required = True
for var, desc in required_vars.items():
    val = os.environ.get(var, "")
    ok = bool(val) and val not in ("sk-...", "pcsk_...", "eyJhbGci...")
    check(f"{var}", ok, f"→ {val[:20]}…" if ok else f"→ MISSING — {desc}")
    if not ok:
        all_required = False

for var, desc in optional_vars.items():
    val = os.environ.get(var, "")
    print(f"  {INFO}  {var} = {val or '(not set — using default)'}")

if not all_required:
    print(f"\n  {FAIL}  Fix missing env vars in backend/.env before continuing.\n")
    sys.exit(1)


# ── 2. OPENAI ──────────────────────────────────────────────────
print("\n🤖  Checking OpenAI…")
try:
    from openai import OpenAI
    client = OpenAI()
    resp = client.models.list()
    models = [m.id for m in resp.data if "gpt" in m.id][:3]
    check("OpenAI API key valid", True, f"GPT models available: {models}")
except Exception as exc:
    check("OpenAI API key valid", False, str(exc))


# ── 3. SUPABASE ────────────────────────────────────────────────
print("\n🗄️   Checking Supabase…")
try:
    from supabase import create_client
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_KEY"]
    db  = create_client(url, key)
    check("Supabase client created", True, url)

    for table in ["bookings", "expenses", "audit_log"]:
        try:
            db.table(table).select("id").limit(1).execute()
            check(f"Table '{table}' exists", True)
        except Exception as exc:
            check(f"Table '{table}' exists", False,
                  f"Run backend/db/schema.sql in Supabase SQL Editor first → {exc}")

except Exception as exc:
    check("Supabase connection", False, str(exc))


# ── 4. PINECONE ────────────────────────────────────────────────
print("\n🌲  Checking Pinecone…")
try:
    from pinecone import Pinecone
    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    check("Pinecone client created", True)

    index_name = os.environ.get("PINECONE_INDEX", "yatra-policy")
    existing   = [idx.name for idx in pc.list_indexes()]

    if index_name in existing:
        idx       = pc.Index(index_name)
        stats     = idx.describe_index_stats()
        vec_count = stats.get("total_vector_count", 0)
        check(
            f"Index '{index_name}' exists", True,
            f"Vectors in index: {vec_count}" + (
                f"\n        {WARN} Index is empty — run ingestion after starting the app:"
                "\n               curl -X POST http://localhost:8000/admin/ingest-policy"
                if vec_count == 0 else ""
            ),
        )
    else:
        check(
            f"Index '{index_name}' exists", False,
            f"Not found — will be auto-created on first ingestion.\n"
            f"        Existing indexes: {existing or 'none'}",
        )

except Exception as exc:
    check("Pinecone connection", False, str(exc))


# ── 5. SUMMARY ─────────────────────────────────────────────────
passed = sum(results)
total  = len(results)
print(f"\n{'='*52}")
print(f"  {'✅' if passed == total else '⚠️ '} {passed}/{total} checks passed")
print(f"{'='*52}")

if passed == total:
    print("""
  🚀  All good! Start the backend with:
        uvicorn main:app --reload --port 8000

  📥  Then ingest policy docs into Pinecone (first-time only):
        curl -X POST http://localhost:8000/admin/ingest-policy

  🧪  Then run the eval suite:
        python tests/eval/run_eval.py
""")
else:
    print("""
  🔧  Fix the failing checks above, then re-run:
        python test_connections.py
""")

sys.exit(0 if passed == total else 1)