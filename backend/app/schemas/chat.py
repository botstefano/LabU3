from pydantic import BaseModel
from typing import List, Optional


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model: str = "mistral-large-latest"
    temperature: float = 0.7


class ChatResponse(BaseModel):
    content: str
    model: str
