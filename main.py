from fastapi import FastAPI, Depends, status, Response, APIRouter
from fastapi.security import OAuth2PasswordRequestForm
from typing import Final, List
from dbLogic import create_db_and_tables, engine, get_session
from contextlib import asynccontextmanager
import redis.io as redis



@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()    # On Startup
    print('Startup')
    yield
    await engine.dispose()
    
    
    
app: Final = FastAPI(lifespan=lifespan)
router: Final = APIRouter(prefix="/auth", tags=["Authentication"])

