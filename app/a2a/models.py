from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class A2ATask(BaseModel):
    type: str
    context: Dict[str, Any] = {}
    parameters: Dict[str, Any] = {}


class A2ARequest(BaseModel):
    agent_id: str
    target_agent: str = Field(default="risk-assistant")
    message_type: str = Field(default="analysis_request")
    task: A2ATask
    callback: Optional[Dict[str, Any]] = None
    correlation_id: str
    priority: Optional[str] = "normal"
    timeout: Optional[int] = 300


class A2AResponse(BaseModel):
    correlation_id: str
    status: str
    agent_id: str = "risk-assistant"
    response_type: str = "immediate"
    data: Dict[str, Any] = {}
    next_actions: Optional[list] = None
    estimated_completion: Optional[str] = None
    error: Optional[Dict[str, Any]] = None
