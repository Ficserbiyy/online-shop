from fastapi import FastAPI, Depends, status, Response, APIRouter, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from typing import Final, List
from dbLogic import create_db_and_tables, engine, get_session, AsyncSession
from contextlib import asynccontextmanager
import redis.asyncio as redis
from models import User, UserBase, Item, Order, OrderItem, settings
from passLogic import decode_access_token, verify_password, create_access_token
from sqlmodel import select



@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()    # On Startup
    print('Startup')
    yield
    await engine.dispose()
    
    
    
app: Final = FastAPI(lifespan=lifespan)
router: Final = APIRouter(prefix="/auth", tags=["Authentication"])



async def get_current_user(request: Request, session: AsyncSession = Depends(get_session)) -> User:
    ''' To get current user '''
    token = request.cookies.get("shopping_session")
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not Authorized",
        )
    email = decode_access_token(token)
    user = await get_user_by_email(session, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User Not Found",
        )
    return user


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    ''' To get user by email '''
    statement = select(User).where(User.email == email)
    result = await session.execute(statement)
    return result.scalars().first()



@router.post("/login")
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_session)
):
    '''   '''
    user = await get_user_by_email(session, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email address or password"
        )
        
    access_token = create_access_token(data={"sub": user.email})
    response.set_cookie(
        key="shopping_session",
        value=access_token,               # JWT token
        httponly=True,     
        max_age=settings.JWT_EXPIRE * 60, # Cookie TTL
        secure=False, 
        samesite="lax" 
    )
    return {"detail": "Successful login"}
