from fastapi import APIRouter, HTTPException
import sys
import os

# Add the project path to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from schemas import RAGRequest, RAGResponse
# from mcp_project.workflow.graph import Workflow  # Temporarily commented out

router = APIRouter()

@router.post("/rag", response_model=RAGResponse)
async def rag_endpoint(request: RAGRequest):
    # Simple response for now
    return RAGResponse(
        answer=f"RAG response for: {request.query}",
        sources=[]
    )
