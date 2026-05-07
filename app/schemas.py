from pydantic import BaseModel, ConfigDict
from datetime import datetime
import uuid

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