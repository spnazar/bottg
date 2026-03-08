"""
storage.py — хранение данных в JSON файлах
"""

import json
import os

SELLERS_FILE  = "sellers.json"
ORDERS_FILE   = "orders.json"
PRODUCTS_FILE = "products.json"


def _read(path: str, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def _write(path: str, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# -------------------------------------------------------
# Продавцы
# -------------------------------------------------------

def get_all_sellers() -> list:
    return _read(SELLERS_FILE, [])


def get_seller(telegram_id: int) -> dict | None:
    for s in get_all_sellers():
        if s["telegram_id"] == telegram_id:
            return s
    return None


def save_seller(telegram_id: int, kaspi_token: str, shop_name: str):
    sellers = get_all_sellers()
    for s in sellers:
        if s["telegram_id"] == telegram_id:
            s["kaspi_token"] = kaspi_token
            s["shop_name"]   = shop_name
            _write(SELLERS_FILE, sellers)
            return
    sellers.append({
        "telegram_id": telegram_id,
        "kaspi_token": kaspi_token,
        "shop_name":   shop_name,
    })
    _write(SELLERS_FILE, sellers)


# -------------------------------------------------------
# Заказы
# -------------------------------------------------------

def is_order_seen(order_id: str) -> bool:
    return order_id in _read(ORDERS_FILE, [])


def mark_order_seen(order_id: str):
    seen = _read(ORDERS_FILE, [])
    if order_id not in seen:
        seen.append(order_id)
        if len(seen) > 10000:
            seen = seen[-10000:]
        _write(ORDERS_FILE, seen)


# -------------------------------------------------------
# Товары для мониторинга цен
# -------------------------------------------------------

def get_products_for_seller(telegram_id: int) -> list:
    """Возвращает список товаров которые продавец добавил для мониторинга"""
    all_products = _read(PRODUCTS_FILE, {})
    return all_products.get(str(telegram_id), [])


def add_product(telegram_id: int, url: str, name: str = ""):
    """Добавляем товар для мониторинга"""
    all_products = _read(PRODUCTS_FILE, {})
    key = str(telegram_id)
    if key not in all_products:
        all_products[key] = []

    # Не добавляем дубликаты
    for p in all_products[key]:
        if p["url"] == url:
            return False

    all_products[key].append({
        "url":        url,
        "name":       name,
        "last_price": None,  # последняя известная цена конкурента
    })
    _write(PRODUCTS_FILE, all_products)
    return True


def remove_product(telegram_id: int, index: int):
    """Удаляем товар из мониторинга по номеру"""
    all_products = _read(PRODUCTS_FILE, {})
    key = str(telegram_id)
    products = all_products.get(key, [])
    if 0 <= index < len(products):
        removed = products.pop(index)
        all_products[key] = products
        _write(PRODUCTS_FILE, all_products)
        return removed
    return None


def update_last_competitor_price(telegram_id: int, url: str, price: int):
    """Сохраняем последнюю цену конкурента чтобы не спамить"""
    all_products = _read(PRODUCTS_FILE, {})
    key = str(telegram_id)
    for p in all_products.get(key, []):
        if p["url"] == url:
            p["last_price"] = price
            _write(PRODUCTS_FILE, all_products)
            return


def get_last_competitor_price(telegram_id: int, url: str) -> int | None:
    for p in get_products_for_seller(telegram_id):
        if p["url"] == url:
            return p.get("last_price")
    return None
