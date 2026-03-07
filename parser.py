"""
parser.py

Парсим цены конкурентов со страниц Kaspi.
Kaspi API не отдаёт цены других продавцов — только парсинг.

Если уведомления о ценах перестали приходить — скорее всего
Kaspi поменял HTML. Открой страницу товара в браузере,
DevTools → Elements, найди блок продавцов и обнови классы ниже.
"""

import aiohttp
import asyncio
import re
import random

from bs4 import BeautifulSoup
from config import DEMO_MODE
from mock_data import fake_competitor_prices

HEADERS = {
    "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9",
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


async def get_min_competitor_price(
    product_url: str,
    my_price: int = 0,
    my_shop_name: str = None,
) -> int | None:
    """
    Возвращает минимальную цену среди конкурентов на этой карточке товара.
    Исключает наш магазин по названию.
    """
    if DEMO_MODE:
        await asyncio.sleep(random.uniform(0.1, 0.5))
        competitors = fake_competitor_prices(my_price or 3000)
        return min(c["price"] for c in competitors) if competitors else None

    sellers = await _fetch_sellers(product_url)
    if not sellers:
        return None

    # Исключаем свой магазин
    competitors = sellers
    if my_shop_name:
        competitors = [s for s in sellers if my_shop_name.lower() not in s["name"].lower()]

    return min(c["price"] for c in competitors) if competitors else None


async def _fetch_sellers(url: str) -> list[dict]:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers=HEADERS,
                timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                if resp.status != 200:
                    print(f"[parser] HTTP {resp.status} — {url}")
                    return []
                html = await resp.text()
    except Exception as e:
        print(f"[parser] Ошибка загрузки: {e}")
        return []

    return _parse_sellers(html)


def _parse_sellers(html: str) -> list[dict]:
    soup    = BeautifulSoup(html, "html.parser")
    sellers = []

    rows = soup.find_all("div", class_=re.compile(r"sellers-table__row(?!s)"))

    for row in rows:
        try:
            name_el  = row.find(class_=re.compile(r"sellers-table__cell.*merchant"))
            price_el = row.find(class_=re.compile(r"sellers-table__cell.*price"))

            if not price_el:
                continue

            name   = name_el.get_text(strip=True) if name_el else "Неизвестно"
            digits = re.sub(r"[^\d]", "", price_el.get_text(strip=True))

            if digits:
                sellers.append({"name": name, "price": int(digits)})

        except Exception:
            continue

    return sellers
