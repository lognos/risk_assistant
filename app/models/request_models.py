from pydantic import BaseModel
from typing import Optional, Dict, Any


class ChatRequest(BaseModel):
    query: str
    context: Dict[str, Any] = {}
    conversation_id: Optional[str] = None
    language: Optional[str] = None  # en|es|fr or auto


class ChatResponse(BaseModel):
    success: bool
    data: Dict[str, Any] = {}
    summary: Optional[str] = None
    language: Optional[str] = None
    error: Optional[Dict[str, Any]] = None
