"""
Expense Routes — backed by Supabase PostgreSQL
Includes file validation for image uploads.
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from agents.expense_agent import parse_receipt_text, parse_receipt_image
from db.supabase_client import insert_expense, get_all_expenses, delete_expense
import base64
from datetime import datetime

router = APIRouter()

MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5MB
ALLOWED_MIME_TYPES  = {"image/jpeg", "image/png", "image/webp", "application/pdf"}

_expense_counter = 0


def _next_expense_id() -> str:
    global _expense_counter
    _expense_counter += 1
    return f"EXP-{str(_expense_counter).zfill(3)}"


@router.post("/parse-text")
async def parse_text_expense(description: str = Form(...)):
    result = await parse_receipt_text(description)
    result["id"]        = _next_expense_id()
    result["logged_at"] = datetime.now().strftime("%d %b %Y, %I:%M %p")
    result["source"]    = "text"
    saved = await insert_expense(result)
    return saved


@router.post("/parse-image")
async def parse_image_expense(file: UploadFile = File(...)):
    # Validate MIME type
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{file.content_type}' not allowed. Accepted: {', '.join(ALLOWED_MIME_TYPES)}",
        )

    contents = await file.read()

    # Validate file size
    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File too large ({len(contents) // 1024}KB). Max allowed: 5MB",
        )

    b64   = base64.b64encode(contents).decode("utf-8")
    mime  = file.content_type or "image/jpeg"
    result = await parse_receipt_image(b64, mime)
    result["id"]        = _next_expense_id()
    result["logged_at"] = datetime.now().strftime("%d %b %Y, %I:%M %p")
    result["source"]    = "image"
    saved = await insert_expense(result)
    return saved


@router.get("/log")
async def get_expense_log():
    return await get_all_expenses()


@router.delete("/log/{expense_id}")
async def delete_expense_entry(expense_id: str):
    deleted = await delete_expense(expense_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Expense {expense_id} not found")
    return {"deleted": expense_id}
