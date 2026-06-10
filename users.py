from models import User, UserBase, UserPublic, UserPatch, UserUpdate
from dbLogic import redis_client, get_session, AsyncSession
from auth import get_current_user
from fastapi import APIRouter, Depends, Response, HTTPException, status, Request
from sqlmodel import select
import json

router = APIRouter(prefix="/users", tags=["Users"])



@router.get("/{email}", response_model=UserPublic)
async def get_user_profile(
    email: str,
    response: Response, 
    session: AsyncSession = Depends(get_session)
):
    ''' To receive a user profile by email '''
    redis_key = f"user:{email}"
    cached_user = await redis_client.get(redis_key)
    
    if cached_user:
        response.headers["Cache-Control"] = "public, max-age=600"
        return json.loads(cached_user)
    
    statement = select(User).where(User.email == email)
    result = await session.execute(statement)
    db_user = result.scalars().first()
    
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    response.headers["Cache-Control"] = "public, max-age=600"
    await redis_client.setex(f"user:{email}", 600, db_user.model_dump_json())
    return db_user



