from fastapi import APIRouter
from app.database import SessionDep
from sqlmodel import select
from app.models import User






router = APIRouter()

@router.get('/users')
async def get_users(session: SessionDep) -> list[User]:
    users = session.exec(select(User)).all()
    return list(users)

@router.post('/users')
async def create_user(username: str,session: SessionDep) -> User:
    user = User(username=username)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

@router.get('/user/{username}')
async def get_user(username:  str,session: SessionDep) -> User:
    user: User | None = session.exec(select(User).where(User.username==username)).first()
    if not user:
        raise Exception("User does not exist")
    return user