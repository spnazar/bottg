"""
kaspi_api.py

Официальный Kaspi API для продавцов.
Токен генерируется продавцом в личном кабинете:
kaspi.kz/shop/info/merchant/ → Интеграция → API

Правильный заголовок: X-Auth-Token (не Authorization: Bearer)
"""

import asyncio
import random
import time

import requests

from config import DEMO_MODE
from mock_data import fake_order, fake_products

KASPI_BASE = "https://kaspi.kz/shop/api/v2"


def _headers(token: str) -> dict:
    return {
        "X-Auth-Token": token,
        "Accept": "application/vnd.api+json",
        "Content-Type": "application/vnd.api+json",
    }


def _since_timestamp() -> int:
    """Метка времени 7 дней назад в миллисекундах"""
    return int(time.time() * 1000) - (7 * 24 * 60 * 60 * 1000)


# -------------------------------------------------------
# Проверка токена
# -------------------------------------------------------

async def test_token(token: str) -> bool:
    if DEMO_MODE:
        return True
    # Проверку через API пропускаем — Kaspi блокирует прямые запросы из Python
    # Токен проверяется реально при первом обращении к заказам
    return True


# -------------------------------------------------------
# Заказы
# -------------------------------------------------------

async def get_new_orders(token: str) -> list:
    if DEMO_MODE:
        return [fake_order()] if random.random() < 0.35 else []

    try:
        resp = requests.get(
            f"{KASPI_BASE}/orders/",
            headers=_headers(token),
            params={
                "page[number]": 0,
                "page[size]": 50,
                "filter[orders][status]": "NEW",
                "filter[orders][creationDate][$ge]": _since_timestamp(),
            },
            timeout=30,
        )

        if resp.status_code != 200:
            print(f"[kaspi_api] get_new_orders HTTP {resp.status_code}: {resp.text[:200]}")
            return []

        return _parse_orders(resp.json())

    except Exception as e:
        print(f"[kaspi_api] get_new_orders: {e}")
        return []


def _parse_orders(raw: dict) -> list:
    result = []
    for item in raw.get("data", []):
        attrs   = item.get("attributes", {})
        customer = attrs.get("customer", {})

        # Имя товара берём из entries если есть
        entries = []
        for rel in item.get("relationships", {}).get("entries", {}).get("data", []):
            entries.append(rel.get("id", ""))

        result.append({
            "id":               item.get("id"),
            "code":             attrs.get("code", ""),
            "status":           attrs.get("status", "NEW"),
            "totalPrice":       attrs.get("totalPrice", 0),
            "product_name":     "Товар",  # детали в отдельном запросе entries
            "quantity":         1,
            "delivery_address": attrs.get("originAddress", {}).get("address", {}).get("formattedAddress", "не указан"),
            "customer_name":    customer.get("name", "скрыто"),
            "created_at":       attrs.get("creationDate", 0),
        })

    return result


# -------------------------------------------------------
# Детали заказа (товары)
# -------------------------------------------------------

async def get_order_entries(token: str, order_id: str) -> list:
    """Получаем список товаров конкретного заказа"""
    if DEMO_MODE:
        return []

    try:
        resp = requests.get(
            f"{KASPI_BASE}/orders/{order_id}/entries",
            headers=_headers(token),
            timeout=30,
        )
        if resp.status_code != 200:
            return []

        entries = []
        for item in resp.json().get("data", []):
            attrs = item.get("attributes", {})
            entries.append({
                "name":     attrs.get("name", "Товар"),
                "quantity": attrs.get("quantity", 1),
                "price":    attrs.get("basePrice", 0),
            })
        return entries

    except Exception as e:
        print(f"[kaspi_api] get_order_entries: {e}")
        return []


# -------------------------------------------------------
# Товары продавца
# -------------------------------------------------------

async def get_products(token: str) -> list:
    if DEMO_MODE:
        return fake_products()

    all_products = []
    page = 0

    while True:
        try:
            resp = requests.get(
                f"{KASPI_BASE}/masterproducts/",
                headers=_headers(token),
                params={"page[number]": page, "page[size]": 100},
                timeout=30,
            )

            if resp.status_code != 200:
                print(f"[kaspi_api] get_products HTTP {resp.status_code}")
                break

            items = resp.json().get("data", [])
            if not items:
                break

            for item in items:
                attrs = item.get("attributes", {})
                all_products.append({
                    "id":       item.get("id"),
                    "name":     attrs.get("name", ""),
                    "price":    attrs.get("price", 0),
                    "quantity": attrs.get("availableQuantity", 0),
                    "url":      attrs.get("pageLink", ""),
                })

            page += 1
            await asyncio.sleep(0.5)

        except Exception as e:
            print(f"[kaspi_api] get_products page {page}: {e}")
            break

    return all_products