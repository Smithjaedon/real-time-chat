# Real-Time Chat App

A real-time chat application built with FastAPI, WebSockets, and SQLite. This project was built as a proof-of-concept focused on real-time communication architecture — designed to serve as a backend foundation that can be dropped into a larger system with full authentication, caching, and other production concerns layered on top.

---

## 🎥 Demo

> _[Add your demo link or video here]_

---

## Tech Stack

| Layer | Tool |
|---|---|
| Backend framework | FastAPI |
| ASGI server | Uvicorn |
| Database | SQLite via SQLModel + SQLAlchemy |
| Real-time | WebSockets |
| Serialization | Pydantic BaseModel |
| Package & env management | uv |

---

## What Was Built

### Project Structure

The codebase is organized so each concern lives in its own file — routers for each model are separated into their own modules, and the WebSocket connection manager lives in its own file. This makes it straightforward to navigate and extend.

```
app/
├── main.py           # App init, middleware, startup
├── database.py       # Engine, session, table creation
├── models.py         # SQLModel table definitions
├── schemas.py        # Pydantic response models
├── routers/
│   ├── users.py
│   ├── rooms.py
│   └── messages.py
└── ws/
    └── manager.py    # ConnectionManager + WebSocket endpoint
```

### Real-Time Features

All real-time functionality runs over WebSockets:

- **Live messaging** — when a user sends a message, all members of that room receive it instantly
- **Typing indicators** — when a user is typing but hasn't sent yet, all room members see the indicator in real time

### Room Management

- Create a new room
- Join an existing room
- View all rooms you're already a member of (shown in the sidebar)
- Edit a room's name

### Authentication

Authentication is intentionally minimal — there's no registration flow or password hashing on the frontend. A user just enters their username, and if that user exists in the system they're in. The backend does support creating users via API. This was a deliberate scoping decision to keep the focus on the real-time layer.

### CORS

CORS is properly configured to allow the frontend dev server origins.

---

## Running Locally

**Prerequisites:** Python 3.11+, [uv](https://github.com/astral-sh/uv)

```bash
# Install dependencies
uv sync

# Run the dev server (from project root)
uvicorn app.main:app --reload

# Or with FastAPI CLI
fastapi dev app/main.py
```

The API will be available at `http://localhost:8000`.  
Interactive docs at `http://localhost:8000/docs`.

---

## API Overview

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/users` | List all users |
| `POST` | `/users` | Create a user |
| `GET` | `/user/{username}` | Get user by username |
| `POST` | `/create_room` | Create a new room |
| `GET` | `/get_rooms` | List all rooms |
| `GET` | `/get_room` | Get a room with its members |
| `GET` | `/get_user_rooms` | Get rooms a user belongs to |
| `GET` | `/get_messages` | Get paginated messages for a room |
| `PATCH` | `/change_room_name` | Rename a room |
| `WS` | `/ws/{room_id}/{client_id}` | WebSocket connection for a room |

---

## WebSocket Protocol

Connect to `/ws/{room_id}/{client_id}`. On connect, the user is automatically added to the room if they aren't already a member.

Messages are JSON:

```json
{ "type": "chat", "room_id": "...", "client_id": "...", "text": "hello" }
```

```json
{ "type": "typing", "room_id": "...", "client_id": "..." }
```

Incoming messages are broadcast to all other connected members of the room.