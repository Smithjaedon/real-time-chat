from datetime import datetime, timezone
from typing import Annotated

from fastapi import FastAPI, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import DateTime
from sqlalchemy.testing import exclude
import uuid
from sqlmodel import SQLModel, Field, Session, create_engine, select, ForeignKey
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse


class Note(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    content: str

class User(SQLModel, table=True):
    id: uuid.UUID | None = Field(default_factory=uuid.uuid4, primary_key=True)
    username: str = Field(max_length=100, unique=True)

class Room(SQLModel, table=True):
    id: uuid.UUID | None = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_type=DateTime)
    name: str | None = None

class Message(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    content: str
    room: int = Field(foreign_key="room.id")
    user: int = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_type=DateTime)


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

    async def connect(self, websocket: WebSocket, room_id: int):
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
        self.active_connections[room_id].append(websocket)

    def disconnect(self, websocket: WebSocket, room_id: int):
        self.active_connections[room_id].remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str, room_id: int , excludes: WebSocket = None):
        for connection in self.active_connections.get(room_id, []):
            if connection != excludes:
                await connection.send_text(message)


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


@app.post('/users')
async def create_user(username: str,session: SessionDep) -> User:
    user = User(username=username)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

@app.websocket("/ws/{room_id}/{client_id}")
async def websocket_room_endpoint(websocket: WebSocket, client_id: int, room_id: int):
    await manager.connect(websocket, room_id)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(f"Client #{client_id} says: {data}", room_id, excludes=websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket, room_id)
        await manager.broadcast(f"Client #{client_id} left the chat", room_id)