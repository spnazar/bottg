"""
Фейковые данные для демо-режима.
Когда DEMO_MODE = False этот файл не используется.
"""
import random
import time

FAKE_PRODUCTS = [
    {"id": "prod_001", "name": "Чехол iPhone 15 Pro — чёрный матовый",     "price": 4500, "quantity": 23, "url": "https://kaspi.kz/shop/p/demo-001"},
    {"id": "prod_002", "name": "Чехол Samsung Galaxy S24 — прозрачный",     "price": 3200, "quantity": 5,  "url": "https://kaspi.kz/shop/p/demo-002"},
    {"id": "prod_003", "name": "Чехол iPhone 14 — кожаный коричневый",      "price": 6800, "quantity": 0,  "url": "https://kaspi.kz/shop/p/demo-003"},
    {"id": "prod_004", "name": "Стекло защитное iPhone 15",                  "price": 2100, "quantity": 41, "url": "https://kaspi.kz/shop/p/demo-004"},
    {"id": "prod_005", "name": "Чехол Xiaomi 13 — силиконовый синий",        "price": 2800, "quantity": 3,  "url": "https://kaspi.kz/shop/p/demo-005"},
    {"id": "prod_006", "name": "Держатель телефона в машину магнитный",      "price": 5500, "quantity": 18, "url": "https://kaspi.kz/shop/p/demo-006"},
    {"id": "prod_007", "name": "Кабель USB-C 1м — быстрая зарядка",         "price": 1800, "quantity": 67, "url": "https://kaspi.kz/shop/p/demo-007"},
]

FAKE_CUSTOMERS = ["Алибек Д.", "Сауле М.", "Дмитрий К.", "Айгерим Н.", "Руслан Т."]

FAKE_ADDRESSES = [
    "Алматы, ул. Абая 10, кв 45",
    "Астана, пр. Республики 22",
    "Алматы, мкр Алмагуль, д 5",
    "Шымкент, ул. Байтурсынова 88",
]

FAKE_SHOPS = ["AliShop", "TechStore_KZ", "PhoneCase_Pro", "MegaCase", "TopShop"]


def fake_order() -> dict:
    available = [p for p in FAKE_PRODUCTS if p["quantity"] > 0]
    product   = random.choice(available)
    quantity  = random.randint(1, 3)
    return {
        "id":               f"ORD-{random.randint(1000000, 9999999)}",
        "status":           "NEW",
        "product_name":     product["name"],
        "quantity":         quantity,
        "totalPrice":       product["price"] * quantity,
        "customer_name":    random.choice(FAKE_CUSTOMERS),
        "delivery_address": random.choice(FAKE_ADDRESSES),
    }


def fake_competitor_prices(my_price: int) -> list[dict]:
    return [
        {"name": random.choice(FAKE_SHOPS), "price": max(500, my_price + random.randint(-900, 1500))}
        for _ in range(random.randint(2, 5))
    ]


def fake_products() -> list:
    return FAKE_PRODUCTS
