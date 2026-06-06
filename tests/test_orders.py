import pytest
from httpx import AsyncClient, ASGITransport
from main import app



@pytest.mark.asyncio
async def test_create_order_workflow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        
        user_data = {"email": "Corey@gmail.com", "password": "password123"}
        await ac.post("/auth/register", json=user_data)
        
        login_response = await ac.post("/auth/login", data={"username": user_data["email"], "password": user_data["password"]})
        assert login_response.status_code == 200

        item_data = {
            "name": "Sublime Text 3",
            "description": "Thing that can't be bought",
            "price": 4.99,
            "stock_quantity": 10
        }
        item_response = await ac.post("/products/", json=item_data)
        assert item_response.status_code == 200
        created_item = item_response.json()
        item_id = created_item["id"]

        order_response = await ac.post(f"/orders/?item_id={item_id}&quantity=3")
        assert order_response.status_code == 201
        assert order_response.json()["detail"] == "Order Successfully created"

        products_response = await ac.get("/products/")
        assert products_response.status_code == 200
        
        products = products_response.json()
        updated_item = next(i for i in products if i["id"] == item_id)
        assert updated_item["stock_quantity"] == 7