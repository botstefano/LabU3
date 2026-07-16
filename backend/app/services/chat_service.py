from typing import List
import httpx
from app.core.config import get_settings
from app.schemas.chat import ChatMessage, ChatRequest, ChatResponse


settings = get_settings()


class ChatService:
    def __init__(self):
        self.api_url = "https://api.mistral.ai/v1/chat/completions"
        self.api_key = settings.mistral_api_key

    async def chat(self, request: ChatRequest) -> ChatResponse:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": request.model,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "temperature": request.temperature,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(self.api_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        return ChatResponse(
            content=data["choices"][0]["message"]["content"],
            model=data["model"],
        )
