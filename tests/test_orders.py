import pytest
from httpx import AsyncClient, ASGITransport
from main import app


pytestmark = pytest.mark.asyncio


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

        
        # Result №1
        res1 = await ac.post("/cart/add", json={"item_id": id1, "quantity": 2})
        assert res1.status_code == 200
        # Result №2
        res2 = await ac.post("/cart/add", json={"item_id": id2, "quantity": 3})
        assert res2.status_code == 200
        
            
        order_response = await ac.post("/orders/")
        assert order_response.status_code == 201
        res_data = order_response.json()
        
        
        assert res_data["detail"] == "Order Successfully created", "Creation Failed"
        print("ORDER_RESPONSE: ", order_response.json())
        
        # (80 * 2) + (15 * 3) = 205:
        assert res_data["total_cost"] == 205.0
        
        cart_response = await ac.get("/cart/")
        assert cart_response.json() == {}, "cart is not empty"

        products_res = await ac.get("/products/")
        products_data = products_res.json()
        products = products_data["products"]
        
        updated_item1 = next(i for i in products if i["id"] == id1)
        updated_item2 = next(i for i in products if i["id"] == id2)
        
        assert updated_item1["stock_quantity"] == 3 # 5 - 2 = 3
        assert updated_item2["stock_quantity"] == 7 # 10 - 3 = 7
        
        
        await ac.post("/cart/add", json={"item_id": id1, "quantity": 5})
        bad_order_response = await ac.post("/orders/")
        
        assert bad_order_response.status_code == 400
        assert bad_order_response.json()["detail"] == f'Available quantity of products "Sublime Text 3" in the store: 3'
        print("BAD_ORDER_RESPONSE: ", bad_order_response.json())

        


async def test_delete_product_by_author(client):
    ''' Testing item deletion'''
    
    await client.post("/auth/register", json={"email": "author@test.com", "password": "pass188"})
    await client.post("/auth/login", data={"username": "author@test.com", "password": "pass188"})
    
    product_data = {"name": "Coffee", "price": 12.99, "description": "PyTesty"}
    response = await client.post("/products/", json=product_data)
    assert response.status_code == 200, f"ITEM CREATION ERROR: {response.status_code} - {response.text}"
    product_id = response.json()["id"]
    
    delete_response = await client.delete(f"/products/{product_id}")
    assert delete_response.status_code == 200
    assert delete_response.json()["detail"] == "Item successfully deleted"



async def test_ownership_check(client):
    ''' Testing if the client receives 403 Forbidden '''
    
    await client.post("/auth/register", json={"email": "author@test.com", "password": "pass188"})
    await client.post("/auth/login", data={"username": "author@test.com", "password": "pass188"})
    
    product_res = await client.post("/products/", json={"name": "Coffee", "price": 10.0, "description": "PyTesty"})
    assert product_res.status_code == 200, f"ITEM CREATION ERROR: {product_res.status_code} - {product_res.text}"
    product_id = product_res.json()["id"]
    
    # Logout
    client.cookies.clear() 
    
    await client.post("/auth/register", json={"email": "user@test.com", "password": "password188"})
    await client.post("/auth/login", data={"username": "user@test.com", "password": "password188"})
    
    delete_res = await client.delete(f"/products/{product_id}")
    assert delete_res.status_code == 403
    assert delete_res.json()["detail"] == "Forbidden: You are not the author of this product!"
