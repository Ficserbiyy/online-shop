from models import User, UserPublic, UserPatch, UserUpdate
from dbLogic import redis_client, get_session, AsyncSession
from auth import get_current_user
from fastapi import APIRouter, Depends, Response, HTTPException
from sqlmodel import select
import json

router = APIRouter(prefix="/users", tags=["Users"])



@router.get("/{email}", response_model=UserPublic)
async def get_user_profile(
    email: str,
    response: Response, 
    session: AsyncSession = Depends(get_session)
):
    ''' Receive the user profile by email '''
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



@router.patch("/me", response_model=UserPublic)
async def patch_user_me(
    user_data: UserPatch,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    ''' Patch the user profile  '''
    old_email = current_user.email
    
    update_dict = user_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(current_user, key, value)
    
    session.add(current_user)
    await session.commit()
    await session.refresh(current_user)
    
    await redis_client.delete(f"user:{old_email}")
    await redis_client.delete(f"user:{current_user.email}")
    return current_user



@router.put("/me", response_model=UserPublic)
async def update_user_me(
    user_data: UserUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    ''' Update the user profile completely '''
    old_email = current_user.email
    
    update_dict = user_data.model_dump()
    for key, value in update_dict.items():
        setattr(current_user, key, value)
    
    session.add(current_user)
    await session.commit()
    await session.refresh(current_user)
    
    await redis_client.delete(f"user:{old_email}")
    await redis_client.delete(f"user:{current_user.email}")
    return current_user



@router.delete("/me", status_code=200)
async def delete_current_user(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    ''' Soft user deletion '''
    current_user.is_active = False
    
    session.add(current_user)
    await session.commit()
    await redis_client.delete(f"user:{current_user.email}")
    return {"detail": "User account has been deleted."}
