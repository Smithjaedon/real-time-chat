from fastapi import WebSocket, WebSocketDisconnect, APIRouter
from sqlmodel import  select
import uuid
from app.database import SessionDep
from app.models import Message, Room, RoomMember, User
import json

router = APIRouter()

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

@router.websocket("/ws/{room_id}/{client_id}")
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