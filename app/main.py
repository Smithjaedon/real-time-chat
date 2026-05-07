from datetime import datetime, timezone
from typing import Annotated
import json
from pydantic import BaseModel, ConfigDict
from fastapi import FastAPI, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import selectinload
import uuid
from sqlmodel import SQLModel, Field, Session, create_engine, select, Relationship
from fastapi.middleware.cors import CORSMiddleware


class Note(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    content: str

class RoomMember(SQLModel, table=True):
    room_id: uuid.UUID = Field(foreign_key="room.id", primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", primary_key=True)

class User(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    username: str = Field(max_length=100, unique=True)
    rooms: list["Room"] = Relationship(back_populates="members", link_model=RoomMember)
    model_config = ConfigDict(from_attributes=True)



class Room(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    name: str | None = None
    members: list["User"] = Relationship(back_populates="rooms", link_model=RoomMember)
    messages: list["Message"] = Relationship(back_populates="room")
    model_config = ConfigDict(from_attributes=True)

class RoomRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    created_at: datetime
    name: str | None = None
    members: list[UserRead] = []
    messages: list[MessageRead] = []

class RoomSidebarRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str | None = None

class RoomModalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str | None = None
    members: list[UserModalRead] = []

class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    content: str
    room_id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime

class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    username: str

class UserModalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    username: str


class Message(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    content: str
    room_id: uuid.UUID = Field(foreign_key="room.id")
    room: Room = Relationship(back_populates="messages")
    user_id: uuid.UUID = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]
app = FastAPI()

origins = [
    "http://localhost:5173",
    "http://localhost:5174"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],

)

@app.on_event("startup")
def on_startup():
    create_db_and_tables()


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room_id: uuid.UUID):
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
        self.active_connections[room_id].append(websocket)

    def disconnect(self, websocket: WebSocket, room_id: uuid.UUID):
        self.active_connections[room_id].remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, payload: str, room_id: uuid.UUID , excludes: WebSocket = None):
        for connection in self.active_connections.get(room_id, []):
            if connection != excludes:
                await connection.send_text(payload)


manager = ConnectionManager()


@app.get('/notes')
async def get_notes(session: SessionDep) -> list[Note]:
    notes = session.exec(select(Note)).all()
    return list(notes)

@app.post('/notes')
async def create_note(note: Note, session: SessionDep) -> Note:
    session.add(note)
    session.commit()
    session.refresh(note)
    return note

@app.get('/users')
async def get_users(session: SessionDep) -> list[User]:
    users = session.exec(select(User)).all()
    return list(users)

@app.get('/user/{username}')
async def get_user(username:  str,session: SessionDep) -> User:
    user: User | None = session.exec(select(User).where(User.username==username)).first()
    if not user:
        raise Exception("User does not exist")
    return user

@app.patch('/change_room_name')
async def change_name(room_id: uuid.UUID, name: str, session: SessionDep) -> Room:
    room: Room = session.exec(select(Room).where(Room.id == room_id)).first()
    if not Room:
        raise Exception("Room does not exist")
    room.name = name
    session.add(room)
    session.commit()
    session.refresh(room)
    return room

@app.post('/users')
async def create_user(username: str,session: SessionDep) -> User:
    user = User(username=username)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

@app.post('/create_room')
async def creat_room(session: SessionDep) -> Room:
    room = Room()
    session.add(room)
    session.commit()
    session.refresh(room)
    return room

@app.get('/get_messages')
async def get_messages(room_id: uuid.UUID, session: SessionDep, limit: int = Query(10, ge=1, le=100), offset: int = Query(0, ge=0)) -> RoomRead:
    room = session.exec(select(Room).where(Room.id == room_id).options(selectinload(Room.messages), selectinload(Room.members))).first()
    messages = session.exec(select(Message).where(Message.room_id == room_id).offset(offset).limit(limit)).all()
    room.messages = messages
    return room

@app.get("/get_user_rooms", response_model=list[RoomSidebarRead])
async def get_user_rooms(client_id: uuid.UUID ,session: SessionDep):
    rooms = session.exec(select(Room).options(selectinload(Room.members)).where(Room.members.any(client_id == client_id))).all()
    return list(rooms)

@app.get('/get_rooms')
async def get_rooms(session: SessionDep) -> list[Room]:
    rooms = session.exec(select(Room)).all()
    return list(rooms)

@app.get('/get_room')
async def get_room(room_id: uuid.UUID, session: SessionDep) -> RoomModalRead:
    room: Room | None = session.exec(select(Room).where(Room.id==room_id)).first()
    members = session.exec(select(User).where(User.rooms.any(Room.id == room_id))).all()
    room.members = members
    if not room:
        raise Exception("Room does not exist")
    return room

@app.websocket("/ws/{room_id}/{client_id}")
async def websocket_room_endpoint(websocket: WebSocket, client_id: uuid.UUID, room_id: uuid.UUID, session: SessionDep):
    await manager.connect(websocket, room_id)
    room = session.exec(select(Room).where(Room.id == room_id)).first()
    user = session.exec(select(User).where(User.id == client_id)).first()

    if user not in room.members:
        member = RoomMember(user_id=client_id, room_id=room_id)
        session.add(member)
        session.commit()
        session.refresh(member)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            if message['type'] == "chat":
                room_identifier, user_identifier = uuid.UUID(message['room_id']), uuid.UUID(message['client_id'])
                msg = Message(content=message['text'], room_id=room_identifier, user_id=user_identifier)
                session.add(msg)
                session.commit()
                session.refresh(msg)
            await manager.broadcast(data, room_id, excludes=websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket, room_id)