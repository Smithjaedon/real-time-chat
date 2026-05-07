from fastapi import APIRouter
from app.database import SessionDep
from sqlmodel import select
from sqlalchemy.orm import selectinload
from app.models import Room, User
from app.schemas import RoomModalRead, RoomSidebarRead
import uuid


router = APIRouter()

@router.patch('/change_room_name')
async def change_name(room_id: uuid.UUID, name: str, session: SessionDep) -> Room:
    room: Room | None = session.exec(select(Room).where(Room.id == room_id)).first()
    if not Room:
        raise Exception("Room does not exist")
    room.name = name
    session.add(room)
    session.commit()
    session.refresh(room)
    return room

@router.post('/create_room')
async def creat_room(session: SessionDep) -> Room:
    room = Room()
    session.add(room)
    session.commit()
    session.refresh(room)
    return room

@router.get("/get_user_rooms", response_model=list[RoomSidebarRead])
async def get_user_rooms(client_id: uuid.UUID ,session: SessionDep):
    rooms = session.exec(select(Room).options(selectinload(Room.members)).where(Room.members.any(client_id == client_id))).all()
    return list(rooms)

@router.get('/get_rooms')
async def get_rooms(session: SessionDep) -> list[Room]:
    rooms = session.exec(select(Room)).all()
    return list(rooms)

@router.get('/get_room')
async def get_room(room_id: uuid.UUID, session: SessionDep) -> RoomModalRead:
    room: Room | None = session.exec(select(Room).where(Room.id==room_id)).first()
    members = session.exec(select(User).where(User.rooms.any(Room.id == room_id))).all()
    room.members = members
    if not room:
        raise Exception("Room does not exist")
    return room