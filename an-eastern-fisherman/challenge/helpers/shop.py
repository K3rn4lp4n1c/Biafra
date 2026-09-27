from pathlib import Path
import json
import random
import requests

def make_shops(Base_DIR: Path, flag: dict) -> dict[str, dict[str, str|list[dict[str, str]]]]:
    path_to_shops = Base_DIR.joinpath("shops.json")
    raw_shops: list[dict] = json.loads(path_to_shops.read_text()) if path_to_shops.exists() else []
    shops: dict[str, dict] = {shop["id"]: shop for shop in raw_shops if "id" in shop}
    shop_selling_flag = random.choice(list(shops.keys()))
    products: list = shops[shop_selling_flag]["products"]
    products.append(flag)
    random.shuffle(products)
    return shops

def req_product_details(shops: dict[str, dict[str, str|list[dict[str, str]]]], productId:str):
    for shopId, shop in shops.items():
        for product in shop.get("products", []):
            if isinstance(product, dict) and product.get("id") == productId:
                return {"shopId": shopId, "product": product}
    return None

def inform_shop_of_delivery(url:str, username:str, productId:str, shop_token:str):
    try:
        resp = requests.post(f"{url}/{productId}", json={
            "username": username,
            "shopToken": shop_token
        }, timeout=5)
        return resp.status_code == 200
    except Exception as e:
        print(f"Error informing shop: {e}")
        return False

def put_product_out_for_delivery(shops: dict[str, dict[str, str|list[dict[str, str]]]], shopId:str, productId:str, username:str, shop_token:str):
    if shopId not in shops:
        return None
    products = shops[shopId].get("products", [])
    deliverables = shops[shopId].get("out-for-delivery", [])
    if not isinstance(products, list):
        return None
    if not isinstance(deliverables, list):
        return None
    for product in products:
        if isinstance(product, dict) and product.get("id") == productId:
            deliverables.append({"id": productId,"username": username,"shopToken": shop_token,**product})
            products.remove(product)
            return product
    return None

def deliver_product(shops: dict[str, dict[str, str|list[dict[str, str]]]], shopId:str, productId:str, username:str, shop_token:str):
    if shopId not in shops:
        return None
    deliverables = shops[shopId].get("out-for-delivery", [])
    if not isinstance(deliverables, list):
        return None
    for item in deliverables:
        if (isinstance(item, dict) and item.get("id") == productId and 
            item.get("username") == username and item.get("shopToken") == shop_token):
            deliverables.remove(item)
            return item
    return None