from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from typing import List
import sys
import os

# Add the project path to sys.path to import existing modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from schemas import ChatRequest, ChatResponse, ErrorResponse
from mcp_project.utils.llm_utils import LLMFactory

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(message: str = Form(...), files: List[UploadFile] = File(None)):
    try:
        llm = LLMFactory.chat()
        response = await llm.ainvoke(f'你是一个友好的AI助手,请温柔回应用户: {message}')
    except Exception as e:
        # 如果LLM调用失败，使用echo作为fallback
        response = f"Echo: {message}"

    return ChatResponse(
        response=response,
        intention='chat',
        confidence=0.8
    )

@router.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    # Placeholder for file upload
    return {"message": "Files uploaded successfully", "count": len(files)}
