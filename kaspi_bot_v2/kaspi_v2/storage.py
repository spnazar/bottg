"""
storage.py

Хранит данные в обычных JSON файлах — никакой базы данных не нужно.
Три файла:
  sellers.json   — продавцы и их токены
  orders.json    — ID заказов которые уже отправили в Telegram
  prices.json    — последние известные цены конкурентов
"""

import json
import os

SELLERS_FILE = "sellers.json"
ORDERS_FILE  = "orders.json"
PRICES_FILE  = "prices.json"


# -------------------------------------------------------
# Вспомогательные функции
# -------------------------------------------------------

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

def get_all_sellers() -> list[dict]:
    return _read(SELLERS_FILE, [])


def get_seller(telegram_id: int) -> dict | None:
    for s in get_all_sellers():
        if s["telegram_id"] == telegram_id:
            return s
    return None


def save_seller(telegram_id: int, kaspi_token: str, shop_name: str):
    sellers = get_all_sellers()

    # Обновляем если уже есть
    for s in sellers:
        if s["telegram_id"] == telegram_id:
            s["kaspi_token"] = kaspi_token
            s["shop_name"]   = shop_name
            _write(SELLERS_FILE, sellers)
            return

    # Добавляем нового
    sellers.append({
        "telegram_id": telegram_id,
        "kaspi_token": kaspi_token,
        "shop_name":   shop_name,
    })
    _write(SELLERS_FILE, sellers)


# -------------------------------------------------------
# Заказы — просто храним ID которые уже обработали
# -------------------------------------------------------

def is_order_seen(order_id: str) -> bool:
    seen = _read(ORDERS_FILE, [])
    return order_id in seen


def mark_order_seen(order_id: str):
    seen = _read(ORDERS_FILE, [])
    if order_id not in seen:
        seen.append(order_id)
        # Храним последние 10 000 заказов чтобы файл не рос бесконечно
        if len(seen) > 10000:
            seen = seen[-10000:]
        _write(ORDERS_FILE, seen)


# -------------------------------------------------------
# Цены — храним последнюю известную цену конкурента
# чтобы не спамить одно и то же уведомление каждые 30 минут
# -------------------------------------------------------

def get_last_competitor_price(seller_id: int, product_id: str) -> int | None:
    prices = _read(PRICES_FILE, {})
    key = f"{seller_id}_{product_id}"
    return prices.get(key)


def save_competitor_price(seller_id: int, product_id: str, price: int):
    prices = _read(PRICES_FILE, {})
    key = f"{seller_id}_{product_id}"
    prices[key] = price
    _write(PRICES_FILE, prices)
