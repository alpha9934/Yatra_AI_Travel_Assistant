"""
Supabase DB Client
Handles all persistent storage for bookings and expenses via PostgreSQL (Supabase).
"""
import os
import logging
from supabase import create_client, Client

logger = logging.getLogger(__name__)

_client: Client | None = None


def get_supabase() -> Client:
    global _client
    if _client is None:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_KEY")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in environment")
        _client = create_client(url, key)
    return _client


# ─── Bookings ────────────────────────────────────────────────────────────────

async def insert_booking(booking: dict) -> dict:
    sb = get_supabase()
    result = sb.table("bookings").insert(booking).execute()
    logger.info("booking_inserted", extra={"booking_id": booking.get("booking_id")})
    return result.data[0] if result.data else booking


async def get_all_bookings() -> list:
    sb = get_supabase()
    result = sb.table("bookings").select("*").order("booked_at", desc=True).execute()
    return result.data or []


async def delete_booking(booking_id: str) -> bool:
    sb = get_supabase()
    result = sb.table("bookings").delete().eq("booking_id", booking_id).execute()
    return len(result.data) > 0


# ─── Expenses ────────────────────────────────────────────────────────────────

async def insert_expense(expense: dict) -> dict:
    sb = get_supabase()
    result = sb.table("expenses").insert(expense).execute()
    logger.info("expense_inserted", extra={"expense_id": expense.get("id")})
    return result.data[0] if result.data else expense


async def get_all_expenses() -> list:
    sb = get_supabase()
    result = sb.table("expenses").select("*").order("logged_at", desc=True).execute()
    return result.data or []


async def delete_expense(expense_id: str) -> bool:
    sb = get_supabase()
    result = sb.table("expenses").delete().eq("id", expense_id).execute()
    return len(result.data) > 0
