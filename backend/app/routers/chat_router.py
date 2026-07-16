from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.routers.deps import get_current_user
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService


router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    service = ChatService()
    return await service.chat(request)
