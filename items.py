from fastapi import APIRouter, Depends, Response, HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from dbLogic import get_session, redis_client
from models import Item, OrderItem, Order, ItemCreate, User
from auth import get_current_user
import json

router = APIRouter(prefix="/products", tags=["Products"])



@router.get("/")
async def get_all_items(response: Response, session: AsyncSession = Depends(get_session)):
    ''' To get all Shop Items. Using Redis and HTTP Caching. '''
    
    redis_key = "items:all"
    cached_data = await redis_client.get(redis_key)
    
    if cached_data:
        response.headers["Cache-Control"] = "public, max-age=60"     # TTL = 60 seconds
        return json.loads(cached_data)
    
    statement = select(Item)
    result = await session.execute(statement)
    items = result.scalars().all()
       
    items_json = [item.model_dump() for item in items]
    await redis_client.set(redis_key, json.dumps(items_json), ex=60) # TTL = 60 seconds
    response.headers["Cache-Control"] = "public, max-age=60"         # TTL = 60 seconds
    return items


@router.post("/", response_model=Item)
async def create_item(
    item_in: ItemCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    ''' Create a product in the store '''
    limit_key = f"limit:items:{current_user.id}"
    current_count = await redis_client.incr(limit_key)
    
    if current_count == 1:
        await redis_client.expire(limit_key, 60)
    
    if current_count > 30:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests at this minute"
        )
        
    db_item = Item(**item_in.model_dump())
    session.add(db_item)
    await session.commit()
    await session.refresh(db_item)
    
    keys_to_delete = await redis_client.keys("items:*")
    if keys_to_delete:
        await redis_client.delete(*keys_to_delete)    
    return db_item






@router.put("/{item_id}")
async def update_product(
    item_id: int,
    item_update: ItemCreate,
    session: AsyncSession = Depends(get_session)
):
    ''' To Update the product '''
    item = await session.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    update_data = item_update.model_dump()
    for key, value in update_data.items():
        setattr(item, key, value)
    
    session.add(item)
    await session.commit()
    await session.refresh(item)
    
    await redis_client.delete("items:all") # Cache invalidation    
    return {"detail": "Item successfully updated", "item": item}


@router.delete("/{item_id}")
async def delete_product(
    item_id: int,
    session: AsyncSession = Depends(get_session)
):
    ''' To delete the product '''
    item = await session.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
        
    await session.delete(item)
    await session.commit()
    
    await redis_client.delete("items:all") # Cache invalidation
    return {"detail": "Item successfully deleted"}
    