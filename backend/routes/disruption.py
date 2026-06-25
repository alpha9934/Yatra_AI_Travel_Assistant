from fastapi import APIRouter
from pydantic import BaseModel
from agents.disruption_agent import handle_disruption

router = APIRouter()

class DisruptionRequest(BaseModel):
    message: str
    history: list = []

@router.post("/")
async def disruption(req: DisruptionRequest):
    data = await handle_disruption(req.message, req.history)
    return data
