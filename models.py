from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime, timezone
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel


class UserBase(SQLModel):
    ''' To Create the User '''
    email: str = Field(unique=True, index=True)
    
class UserCreate(UserBase):
    ''' For User Registration '''
    password: str = Field(min_length=4)

class User(UserBase, table=True):
    ''' User '''
    id: int | None = Field(primary_key=True, default=None)
    is_active: bool = True
    hashed_password: str
    orders: list["Order"] = Relationship(back_populates="user")
    description: str | None = None
    
class UserPatch(SQLModel):
    ''' To patch the user profile '''
    email: str | None = None
    description: str | None = None

class UserUpdate(SQLModel):
    ''' To completely update the user profile '''
    email: str
    description: str | None = None

class UserPublic(UserBase):
    ''' Public User Profile '''
    id: int 
    description: str | None
    is_active: bool = True
    
class ItemCreate(SQLModel):
    ''' To Create an Item in the store '''
    name: str = Field(index=True)
    description: str
    price: float
    stock_quantity: int = 0

class ItemPatch(SQLModel):
    ''' To PATCH the item '''
    name: str | None = None
    description: str | None = None
    price: float | None = None
    stock_quantity: int | None = None

class Item(ItemCreate, table=True):
    ''' Item '''
    id: int | None = Field(primary_key=True, default=None)
    owner_id: int = Field(foreign_key="user.id")

class Order(SQLModel, table=True):
    ''' Order '''
    id: int | None = Field(primary_key=True, default=None)
    user_id: int = Field(foreign_key="user.id")
    total_price: float
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    user: "User" = Relationship(back_populates="orders")

class OrderItem(SQLModel, table=True):
    ''' Link Table ''' 
    order_id: int = Field(foreign_key="order.id", primary_key=True)
    item_id: int = Field(foreign_key="item.id",ondelete="CASCADE", primary_key=True)
    quantity: int = 1

class OrderItemCreate(SQLModel):
    ''' Items used when creating an order '''
    item_id: int
    quantity: int

class OrderCreate(SQLModel):
    ''' To create an order '''
    items: list[OrderItemCreate]   

class CartUpdate(SQLModel):
    ''' To update the cart '''
    item_id: int
    quantity: int    

class Settings(BaseSettings):
    ''' Enviroment Settings '''
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "password"
    DB_HOST: str = "db" 
    DB_NAME: str = "shop"
    TEST_DB_NAME: str = 'shop_test'
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
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}/{self.DB_NAME}"
    @property
    def TEST_DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:5432/{self.TEST_DB_NAME}"

settings = Settings()
