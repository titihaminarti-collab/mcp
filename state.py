from dataclasses import dataclass, field
from typing import Any, Dict, Optional, TypedDict, Literal, List


class WorkflowState(TypedDict):
    user_input: str
    user_preference: str
    intention: Literal['chat','travel','rag']
    intention_confidence: float
    travel_intent: Literal['ticket','hotel','baidu']
    travel_intent_confidence: float
    sub_intent: str
    sub_intent_confidence: float
    execution_path: List[str]
    history:List[Dict[str,str]]
    final_output: str

    searched_tickets: List[Dict[str, Any]]
    searched_hotels: List[Dict[str, Any]]
    summary_tickets: str
    summary_hotels: str
    reviewed_tickets: str
    reviewed_hotels: str
    review_pass: bool
    needs_retry: bool
    ticket_retry_count: int
    hotel_retry_count: int
    error_msg: str


@dataclass
class AgentResponse:
    success: bool
    content: Any
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)