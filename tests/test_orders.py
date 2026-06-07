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

        # Item №1
        item1_res = await ac.post("/products/", json={
            "name": "Sublime Text 3",
            "description": "Thing that can't be bought",
            "price": 80.0,
            "stock_quantity": 5
        })
        id1 = item1_res.json()["id"]

        # Item №2
        item2_res = await ac.post("/products/", json={
            "name": "Coffee",
            "description": "To code 8 hours a day",
            "price": 15.0,
            "stock_quantity": 10
        })
        id2 = item2_res.json()["id"]
        
        
        
        order_payload = {
            "items": [
                {"item_id": id1, "quantity": 2},
                {"item_id": id2, "quantity": 3}
            ]
        }
        order_response = await ac.post("/orders/", json=order_payload)
        
        assert order_response.status_code == 201
        res_data = order_response.json()
        assert res_data["detail"] == "Order Successfully created", "Creation Failed"
        
        # (80 * 2) + (15 * 3) = 205:
        assert res_data["total_cost"] == 205.0

        products_res = await ac.get("/products/")
        products = products_res.json()
        
        updated_item1 = next(i for i in products if i["id"] == id1)
        updated_item2 = next(i for i in products if i["id"] == id2)
        
        assert updated_item1["stock_quantity"] == 3 # 5 - 2 = 3
        assert updated_item2["stock_quantity"] == 7 # 10 - 3 = 7