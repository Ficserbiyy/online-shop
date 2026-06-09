from fastapi import APIRouter, Depends, Response, HTTPException, status, Request
from sqlmodel import select, col
from sqlmodel.ext.asyncio.session import AsyncSession
from dbLogic import get_session, redis_client
from models import Item, OrderItem, Order, ItemCreate, User, ItemPatch
from auth import get_current_user
import json
import hashlib

router = APIRouter(prefix="/products", tags=["Products"])



@router.get("/")
async def get_all_products(
    request: Request, 
    response: Response, 
    search: str | None = None,
    order_by: str | None = None,
    page: int = 1,
    limit: int = 10,
    session: AsyncSession = Depends(get_session)
):
    ''' To get all the items from the store. '''
    
    statement = select(Item)
    if search:
        statement = statement.where(col(Item.name).ilike(f"%{search}%"))
        
    match order_by:
        case "price_asc":
            statement = statement.order_by(col(Item.price))
        case "price_desc":
            statement = statement.order_by(col(Item.price).desc())
        case "id_desc":
            statement = statement.order_by(col(Item.id).desc())
        case _:
            statement = statement.order_by(col(Item.id))
        
        
    offset = (page - 1) * limit
    statement = statement.offset(offset).limit(limit)
    result = await session.execute(statement)
    products = result.scalars().all()
    
    result_data = {
        "page": page,
        "limit": limit,
        "search_query": search,
        "products": [p.model_dump() for p in products]
    }
    
    # ETag generation
    json_bytes = json.dumps(result_data, sort_keys=True).encode("utf-8")
    generated_etag = f'W/"{hashlib.md5(json_bytes).hexdigest()}"'
    
    # If-None-Match check
    client_etag = request.headers.get("If-None-Match")
    if client_etag == generated_etag:
        # If the resource hasn't changed, The server responds with 304 Not Modified:
        response.status_code = 304
        return Response(status_code=304)
        
    # If the resource has changed, The server sends a 200 OK status along with the newly updated content:
    response.headers["ETag"] = generated_etag
    response.headers["Cache-Control"] = "no-cache"
    return result_data



@router.get("/{item_id}", response_model=Item)
async def get_single_item(item_id: int, response: Response, session: AsyncSession = Depends(get_session)):
    ''' To get one item from the store by ID. Using Redis and HTTP Caching. '''
    
    redis_key = f"items:{item_id}"
    cached_data = await redis_client.get(redis_key)
    
    if cached_data:
        response.headers["Cache-Control"] = "public, max-age=60"     
        return json.loads(cached_data)
    
    item = await session.get(Item, item_id)     
    if not item:
        raise HTTPException(status_code=404, detail="Product not found")
    
    await redis_client.set(redis_key, item.model_dump_json(), ex=60) 
    response.headers["Cache-Control"] = "public, max-age=60"         
    return item




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
        
    db_item = Item.model_validate(item_in, update={"owner_id": current_user.id})    
    session.add(db_item)
    await session.commit()
    await session.refresh(db_item)
    
    await redis_client.delete("items:all")
    return db_item





@router.put("/{item_id}")
async def update_product(
    item_id: int,
    item_update: ItemCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    ''' To Update the product completely '''
    item = await session.get(Item, item_id)
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if item.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden: You are not the author of this product!")
    
    update_data = item_update.model_dump()
    for key, value in update_data.items():
        setattr(item, key, value)
    
    session.add(item)
    await session.commit()
    await session.refresh(item)
    
    await redis_client.delete("items:all") # Cache invalidation    
    await redis_client.delete(f"items:{item_id}")    
    return {"detail": "Item successfully updated", "item": item}





@router.patch("/{item_id}")
async def patch_product(
    item_id: int,
    item_update: ItemPatch,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    ''' To Update the product '''
    item = await session.get(Item, item_id)
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if item.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden: You are not the author of this product!")
    
    update_data = item_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item, key, value)
    
    session.add(item)
    await session.commit()
    await session.refresh(item)
    
    await redis_client.delete("items:all") # Cache invalidation    
    await redis_client.delete(f"items:{item_id}")    
    return {"detail": "Item successfully updated", "item": item}

    


@router.delete("/{item_id}")
async def delete_product(
    item_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    ''' To delete the product '''
    item = await session.get(Item, item_id)
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if item.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden: You are not the author of this product!")
        
    await session.delete(item)
    await session.commit()
    
    await redis_client.delete("items:all") # Cache invalidation
    await redis_client.delete(f"items:{item_id}")
    return {"detail": "Item successfully deleted"}
    