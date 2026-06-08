from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
from sqlalchemy.orm import joinedload
from dbLogic import get_session, redis_client, AsyncSession
from models import User, Order, OrderItem, Item, OrderCreate
from auth import get_current_user 
import json

router = APIRouter(prefix="/orders", tags=["Orders"])




@router.post("/", status_code=201)
async def create_multi_item_order(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    ''' To make an order with multiple items '''
    assert current_user.id is not None, "User ID cannot be None"
    redis_key = f"cart:{current_user.id}"
    
    cart_data = await redis_client.get(redis_key)
    if not cart_data:
        raise HTTPException(status_code=400, detail="Your cart is empty")
        
    cart = json.loads(cart_data)
    if not cart:
        raise HTTPException(status_code=400, detail="Your cart is empty")
        
    total_price = 0.0
    items_to_buy = []
    
    for str_item_id, quantity in cart.items():
        item_id = int(str_item_id)
        item = await session.get(Item, item_id)
        
        if not item:
            raise HTTPException(status_code=404, detail=f"Product with ID={item_id} not found")
            
        if item.stock_quantity < quantity:
            raise HTTPException(
                status_code=400, 
                detail=f'Available quantity of products "{item.name}" in the store: {item.stock_quantity}'
            )
        
        total_price += item.price * quantity
        items_to_buy.append((item, quantity))
    
    # Creating one main order
    new_order = Order(user_id=current_user.id, total_price=total_price)
    session.add(new_order)
    await session.commit()
    await session.refresh(new_order)
    
    assert new_order.id is not None, "Order ID cannot be None"
    for item, quantity in items_to_buy:
        assert item.id is not None, "Item ID cannot be None"
        
        # Linking Many-to-Many
        link = OrderItem(order_id=new_order.id, item_id=item.id, quantity=quantity)
        session.add(link)
        
        item.stock_quantity -= quantity
        session.add(item)
        
    await session.commit()
    # Cache invalidation
    await redis_client.delete(redis_key)
    await redis_client.delete("items:all")
    return {"detail": "Order Successfully created", "order_id": new_order.id, "total_cost": total_price}
