from fastapi import FastAPI, Depends, status, Response, APIRouter, HTTPException, Request
from typing import Final, List
from dbLogic import create_db_and_tables, engine, get_session, AsyncSession, redis_client
from contextlib import asynccontextmanager
from models import User, UserBase, Item, Order, OrderItem, settings
from sqlmodel import select
from auth import router as auth_router
from items import router as item_router
from orders import router as order_router
from cart import router as cart_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    yield
    await redis_client.aclose()
    await engine.dispose()
    
       
app: Final = FastAPI(title="Shop API", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(item_router)
app.include_router(order_router)
app.include_router(cart_router)



@app.get("/")
async def root():
    return {"message": "Welcome"}





