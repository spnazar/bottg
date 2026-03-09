"""
storage.py — хранение данных в MongoDB Atlas

Данные хранятся в облаке — не сбрасываются при перезапуске Railway.
"""

import os
from pymongo import MongoClient

MONGO_URL = os.environ.get("MONGO_URL", "")

_client = None
_db     = None


def _get_db():
    global _client, _db
    if _db is None:
        url = os.environ.get("MONGO_URL", "NOT_FOUND")
        print(f"[storage] MONGO_URL: {url[:30]}...")
        _client = MongoClient(url)
        _db     = _client["kaspi"]
    return _db


# -------------------------------------------------------
# Продавцы
# -------------------------------------------------------

def get_all_sellers() -> list:
    db = _get_db()
    return list(db.sellers.find({}, {"_id": 0}))


def get_seller(telegram_id: int) -> dict | None:
    db = _get_db()
    return db.sellers.find_one({"telegram_id": telegram_id}, {"_id": 0})


def save_seller(telegram_id: int, kaspi_token: str, shop_name: str):
    db = _get_db()
    db.sellers.update_one(
        {"telegram_id": telegram_id},
        {"$set": {"telegram_id": telegram_id, "kaspi_token": kaspi_token, "shop_name": shop_name}},
        upsert=True
    )


# -------------------------------------------------------
# Заказы
# -------------------------------------------------------

def is_order_seen(order_id: str) -> bool:
    db = _get_db()
    return db.orders.find_one({"order_id": order_id}) is not None


def mark_order_seen(order_id: str):
    db = _get_db()
    db.orders.update_one(
        {"order_id": order_id},
        {"$set": {"order_id": order_id}},
        upsert=True
    )


# -------------------------------------------------------
# Товары для мониторинга цен
# -------------------------------------------------------

def get_products_for_seller(telegram_id: int) -> list:
    db = _get_db()
    seller = db.sellers.find_one({"telegram_id": telegram_id}, {"_id": 0})
    return seller.get("products", []) if seller else []


def add_product(telegram_id: int, url: str, name: str = "") -> bool:
    db = _get_db()
    seller = db.sellers.find_one({"telegram_id": telegram_id})
    if not seller:
        return False

    products = seller.get("products", [])
    for p in products:
        if p["url"] == url:
            return False  # уже есть

    products.append({"url": url, "name": name, "last_price": None})
    db.sellers.update_one(
        {"telegram_id": telegram_id},
        {"$set": {"products": products}}
    )
    return True


def remove_product(telegram_id: int, index: int) -> dict | None:
    db = _get_db()
    seller = db.sellers.find_one({"telegram_id": telegram_id})
    if not seller:
        return None

    products = seller.get("products", [])
    if 0 <= index < len(products):
        removed = products.pop(index)
        db.sellers.update_one(
            {"telegram_id": telegram_id},
            {"$set": {"products": products}}
        )
        return removed
    return None


def update_last_competitor_price(telegram_id: int, url: str, price: int):
    db = _get_db()
    seller = db.sellers.find_one({"telegram_id": telegram_id})
    if not seller:
        return

    products = seller.get("products", [])
    for p in products:
        if p["url"] == url:
            p["last_price"] = price
            break

    db.sellers.update_one(
        {"telegram_id": telegram_id},
        {"$set": {"products": products}}
    )


def get_last_competitor_price(telegram_id: int, url: str) -> int | None:
    for p in get_products_for_seller(telegram_id):
        if p["url"] == url:
            return p.get("last_price")
    return None
