from pydantic import ConfigDict
from datetime import datetime, timezone
import uuid
from sqlmodel import SQLModel, Field, Relationship

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


class Message(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    content: str
    room_id: uuid.UUID = Field(foreign_key="room.id")
    room: Room = Relationship(back_populates="messages")
    user_id: uuid.UUID = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))