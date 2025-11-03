from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = "default"

class ActionOutput(BaseModel):
    action: Optional[str] = None
    functionName: Optional[str] = None
    arguments: Dict[str, Any] = {}

class AssistantResponse(BaseModel):
    response: str
    timestamp: str
    session_id: str

class HealthResponse(BaseModel):
    status: str
    message: str
    timestamp: str
