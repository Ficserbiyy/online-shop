from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from pydantic_settings import BaseSettings, SettingsConfigDict



class UserBase(SQLModel):
    ''' To Create User'''
    email: str = Field(unique=True)

class User(UserBase, table=True):
    '''User '''
    id: int | None = Field(primary_key=True, default=None)
    hashed_password: str
    is_active: bool = Field(default=True)
    orders: list["Order"] = Relationship(back_populates="user")
    
class Item(SQLModel, table=True):
    ''' Item '''
    id: int | None = Field(primary_key=True, default=None)
    name: str = Field(index=True)
    description: str
    price: float
    stock_quantity: int = Field(default=0)
    
class Order(SQLModel, table=True):
    ''' Order '''
    id: int | None = Field(primary_key=True, default=None)
    user_id: int = Field(foreign_key="user.id")
    total_price: float
    created_at: datetime = Field(default_factory=datetime.utcnow)
    user: "User" = Relationship(back_populates="orders")

class OrderItem(SQLModel, table=True):
    ''' Link Table ''' 
    order_id: int = Field(foreign_key="order.id", primary_key=True)
    item_id: int = Field(foreign_key="item.id", primary_key=True)
    quantity: int = Field(default=1)

class Settings(BaseSettings):
    ''' Enviroment Settings '''
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "password"
    DB_HOST: str = "db" 
    DB_NAME: str = "shop"
    REDIS_URL: str = 'redis://redis:6379'
    SECRET_KEY: str = ''
    JWT_ALGORITHM: str = 'HS256'
    JWT_EXPIRE: int = 30
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        extra='ignore',
        case_sensitive=False
    )

settings = Settings()
