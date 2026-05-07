from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import create_db_and_tables
from app.routers import users, rooms, messages
from app.ws.manager import router as ws_router

app = FastAPI()
app.include_router(users.router)
app.include_router(rooms.router)
app.include_router(messages.router)
app.include_router(ws_router)


origins = [
    "http://localhost:5173",
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