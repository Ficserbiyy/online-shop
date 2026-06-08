from fastapi import APIRouter, Depends, HTTPException
from dbLogic import redis_client
from auth import get_current_user
from models import User, CartUpdate
from typing import Final
import json

router:Final = APIRouter(prefix="/cart", tags=["Cart"])

# The cart is stored in the cache for 24 hours after creation:
CART_TTL: Final = 86400  



@router.post("/add")
async def add_to_cart(cart_in: CartUpdate, current_user: User = Depends(get_current_user)):
    ''' To add item to the cart '''
    
    redis_key = f"cart:{current_user.id}"
    cart_data = await redis_client.get(redis_key)
    cart = json.loads(cart_data) if cart_data else {} # Empty, if the TTL has expired
    
    str_item_id = str(cart_in.item_id)
    if cart_in.quantity <= 0:
        cart.pop(str_item_id, None) # deleting an item
    else:
        cart[str_item_id] = cart_in.quantity
   
    await redis_client.set(redis_key, json.dumps(cart), ex=CART_TTL)
    
    return {"detail": "Cart updated", "current_cart": cart}


@router.get("/")
async def get_cart(current_user: User = Depends(get_current_user)):
    ''' To view the user's cart '''
    redis_key = f"cart:{current_user.id}"
    cart_data = await redis_client.get(redis_key)
    return json.loads(cart_data) if cart_data else {}