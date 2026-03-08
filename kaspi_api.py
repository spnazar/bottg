"""
kaspi_api.py
"""

import random
import time
import httpx

from config import DEMO_MODE
from mock_data import fake_order, fake_products

KASPI_BASE = "https://kaspi.kz/shop/api/v2"


def _headers(token: str) -> dict:
    return {
        "X-Auth-Token": token,
        "Accept": "application/vnd.api+json",
        "Content-Type": "application/vnd.api+json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }


def _since_timestamp() -> int:
    # Только последние 2 часа — чтобы не приходили старые заказы
    return int(time.time() * 1000) - (2 * 60 * 60 * 1000)


async def _fetch(token: str, url: str, params: dict = None) -> dict | None:
    try:
        async with httpx.AsyncClient(
            headers=_headers(token),
            timeout=60.0,
            verify=False,
            follow_redirects=True,
        ) as client:
            resp = await client.get(url, params=params)
            print(f"[kaspi_api] {url} → {resp.status_code}")
            if resp.status_code == 200:
                return resp.json()
            print(f"[kaspi_api] Ответ: {resp.text[:300]}")
            return None
    except Exception as e:
        print(f"[kaspi_api] error: {type(e).__name__}: {e}")
        return None


async def test_token(token: str) -> bool:
    if DEMO_MODE:
        return True
    return True


async def get_new_orders(token: str) -> list:
    if DEMO_MODE:
        return [fake_order()] if random.random() < 0.35 else []

    data = await _fetch(
        token,
        f"{KASPI_BASE}/orders/",
        params={
            "page[number]": 0,
            "page[size]": 50,
            "filter[orders][status]": "APPROVED_BY_BANK",
            "filter[orders][creationDate][$ge]": _since_timestamp(),
        }
    )

    if not data:
        return []

    return _parse_orders(data)


async def get_order_entries(token: str, order_id: str) -> list:
    if DEMO_MODE:
        return []

    data = await _fetch(token, f"{KASPI_BASE}/orders/{order_id}/entries")
    if not data:
        return []

    entries = []
    for item in data.get("data", []):
        attrs = item.get("attributes", {})
        entries.append({
            "name":     attrs.get("name", "Товар"),
            "quantity": attrs.get("quantity", 1),
            "price":    attrs.get("basePrice", 0),
        })
    return entries


def _parse_orders(raw: dict) -> list:
    result = []
    for item in raw.get("data", []):
        attrs    = item.get("attributes", {})
        customer = attrs.get("customer", {})
        result.append({
            "id":               item.get("id"),
            "code":             attrs.get("code", ""),
            "status":           attrs.get("status", ""),
            "totalPrice":       attrs.get("totalPrice", 0),
            "product_name":     "Товар",
            "quantity":         1,
            "delivery_address": attrs.get("deliveryAddress", {}).get("formattedAddress", "не указан"),
            "customer_name":    customer.get("name", "скрыто"),
            "created_at":       attrs.get("creationDate", 0),
        })
    return result


async def get_products(token: str) -> list:
    if DEMO_MODE:
        return fake_products()
    return []
