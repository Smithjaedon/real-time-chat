from fastapi import Query, APIRouter
from app.database import SessionDep
from sqlmodel import select
from sqlalchemy.orm import selectinload
from app.models import Message, Room
from app.schemas import RoomRead
import uuid

router = APIRouter()

@router.get('/get_messages')
async def get_messages(room_id: uuid.UUID, session: SessionDep, limit: int = Query(10, ge=1, le=100), offset: int = Query(0, ge=0)) -> RoomRead:
    room = session.exec(select(Room).where(Room.id == room_id).options(selectinload(Room.messages), selectinload(Room.members))).first()
    messages = session.exec(select(Message).where(Message.room_id == room_id).offset(offset).limit(limit)).all()
    room.messages = messages
    return room