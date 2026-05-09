from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class ChatRequest(BaseModel):
    message: str
    files: Optional[List[bytes]] = None  # For file uploads

class ChatResponse(BaseModel):
    response: str
    intention: Optional[str] = None
    confidence: Optional[float] = None

class RAGRequest(BaseModel):
    query: str

class RAGResponse(BaseModel):
    answer: str
    sources: Optional[List[Dict[str, Any]]] = None

class ErrorResponse(BaseModel):
    error: str
    details: Optional[str] = None
