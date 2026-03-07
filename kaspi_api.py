"""
kaspi_api.py
"""

import asyncio
import random
import time
import json
import os

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
    return int(time.time() * 1000) - (7 * 24 * 60 * 60 * 1000)


async def _fetch(token: str, url: str, params: dict = None) -> dict | None:
    from playwright.async_api import async_playwright

    if params:
        query = "&".join(f"{k}={v}" for k, v in params.items())
        full_url = f"{url}?{query}"
    else:
        full_url = url

    # Ищем chromium в системе
    chromium_paths = [
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/usr/bin/google-chrome",
        "/nix/store",  # Railway nix путь
    ]

    try:
        async with async_playwright() as p:
            # Пробуем найти системный браузер
            executable = None
            for path in chromium_paths:
                if os.path.exists(path) and os.path.isfile(path):
                    executable = path
                    break

            launch_opts = {"headless": True}
            if executable:
                launch_opts["executable_path"] = executable
                print(f"[kaspi_api] Используем браузер: {executable}")

            browser = await p.chromium.launch(**launch_opts)
            context = await browser.new_context(
                extra_http_headers=_headers(token)
            )
            page = await context.new_page()
            resp = await page.goto(full_url, timeout=30000)
            body = await resp.body()
            text = body.decode("utf-8")
            await browser.close()
            return json.loads(text)

    except Exception as e:
        print(f"[kaspi_api] _fetch error: {e}")
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
            "filter[orders][status]": "NEW",
            "filter[orders][creationDate][$ge]": _since_timestamp(),
        }
    )

    if not data:
        return []

    return _parse_orders(data)


def _parse_orders(raw: dict) -> list:
    result = []
    for item in raw.get("data", []):
        attrs    = item.get("attributes", {})
        customer = attrs.get("customer", {})
        result.append({
            "id":               item.get("id"),
            "code":             attrs.get("code", ""),
            "status":           attrs.get("status", "NEW"),
            "totalPrice":       attrs.get("totalPrice", 0),
            "product_name":     "Товар",
            "quantity":         1,
            "delivery_address": attrs.get("originAddress", {}).get("address", {}).get("formattedAddress", "не указан"),
            "customer_name":    customer.get("name", "скрыто"),
            "created_at":       attrs.get("creationDate", 0),
        })
    return result


async def get_products(token: str) -> list:
    if DEMO_MODE:
        return fake_products()

    data = await _fetch(
        token,
        f"{KASPI_BASE}/masterproducts/",
        params={"page[number]": 0, "page[size]": 100}
    )

    if not data:
        return []

    products = []
    for item in data.get("data", []):
        attrs = item.get("attributes", {})
        products.append({
            "id":       item.get("id"),
            "name":     attrs.get("name", ""),
            "price":    attrs.get("price", 0),
            "quantity": attrs.get("availableQuantity", 0),
            "url":      attrs.get("pageLink", ""),
        })

    return products
