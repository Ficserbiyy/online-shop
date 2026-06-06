from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
from sqlalchemy.orm import joinedload
from dbLogic import get_session, redis_client, AsyncSession
from models import User, Order, OrderItem, Item
from auth import get_current_user 

router = APIRouter(prefix="/orders", tags=["Orders"])



@router.post("/", status_code=201)
async def create_order(
    item_id: int, 
    quantity: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    ''' To make an order '''
    item = await session.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
        
    if item.stock_quantity < quantity:
        raise HTTPException(
            status_code=400, 
            detail=f"Available quantity of products in the store: {item.stock_quantity}"
        )
    assert current_user.id is not None, "User ID cannot be None"    
    total_price = item.price * quantity
    new_order = Order(user_id=current_user.id, total_price=total_price)
    
    session.add(new_order)
    await session.commit()
    await session.refresh(new_order)
    
    assert new_order.id is not None, "Order ID cannot be None"
    assert item.id is not None, "Item ID cannot be None"
    
    # Using linktable (OrderItem)
    order_item = OrderItem(order_id=new_order.id, item_id=item.id, quantity=quantity)
    session.add(order_item)
    item.stock_quantity -= quantity
    session.add(item)
    
    await session.commit()
    await redis_client.delete("items:all")
    return {"detail": " Order Successfully created ", "order_id": new_order.id}
