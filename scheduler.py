"""
scheduler.py — фоновые задачи
"""

import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot

from config import CHECK_ORDERS_INTERVAL, CHECK_PRICES_INTERVAL, CHECK_STOCK_INTERVAL
from storage import (
    get_all_sellers, is_order_seen, mark_order_seen,
    get_products_for_seller, get_last_competitor_price, update_last_competitor_price
)
from kaspi_api import get_new_orders
from parser import get_min_competitor_price


# -------------------------------------------------------
# Заказы
# -------------------------------------------------------

async def _check_orders(bot: Bot, seller: dict):
    try:
        orders = await get_new_orders(seller["kaspi_token"])
        for order in orders:
            order_id = str(order.get("id", ""))
            if not is_order_seen(order_id):
                mark_order_seen(order_id)
                await _send_order(bot, seller["telegram_id"], order)
    except Exception as e:
        print(f"[scheduler] Заказы {seller['telegram_id']}: {e}")


async def check_all_orders(bot: Bot):
    print("[scheduler] Проверяем заказы...")
    tasks = [_check_orders(bot, s) for s in get_all_sellers()]
    await asyncio.gather(*tasks, return_exceptions=True)


# -------------------------------------------------------
# Цены конкурентов
# -------------------------------------------------------

async def _check_prices(bot: Bot, seller: dict):
    products = get_products_for_seller(seller["telegram_id"])
    if not products:
        return

    shop_name = seller.get("shop_name", "")

    for product in products:
        url      = product.get("url", "")
        name     = product.get("name", url)

        if not url:
            continue

        try:
            min_price = await get_min_competitor_price(
                url,
                my_shop_name=shop_name,
            )

            if min_price is None:
                continue

            # Уведомляем только если цена изменилась с прошлого раза
            last = get_last_competitor_price(seller["telegram_id"], url)
            if last != min_price:
                update_last_competitor_price(seller["telegram_id"], url, min_price)
                await _send_price_alert(bot, seller["telegram_id"], name, min_price)

            await asyncio.sleep(2)

        except Exception as e:
            print(f"[scheduler] Цена для {url}: {e}")


async def check_all_prices(bot: Bot):
    print("[scheduler] Проверяем цены конкурентов...")
    for seller in get_all_sellers():
        await _check_prices(bot, seller)
        await asyncio.sleep(2)


# -------------------------------------------------------
# Уведомления
# -------------------------------------------------------

async def _send_order(bot: Bot, telegram_id: int, order: dict):
    total = order.get("totalPrice", 0)
    await bot.send_message(
        telegram_id,
        f"🛒 <b>Новый заказ!</b>\n\n"
        f"💰 <b>Сумма:</b> {total:,.0f} ₸\n"
        f"👤 <b>Покупатель:</b> {order.get('customer_name', 'скрыто')}\n"
        f"📍 <b>Адрес:</b> {order.get('delivery_address', 'не указан')}\n\n"
        f"🔖 Номер: <code>{order.get('code', order.get('id', '—'))}</code>",
        parse_mode="HTML",
    )


async def _send_price_alert(bot: Bot, telegram_id: int, product_name: str, min_price: int):
    await bot.send_message(
        telegram_id,
        f"⚠️ <b>Изменение цены у конкурента!</b>\n\n"
        f"📦 {product_name}\n\n"
        f"🔻 Минимальная цена конкурента: <b>{min_price:,} ₸</b>\n\n"
        f"Проверьте свою цену на Kaspi.",
        parse_mode="HTML",
    )


# -------------------------------------------------------
# Планировщик
# -------------------------------------------------------

def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="Asia/Almaty")
    scheduler.add_job(check_all_orders, "interval", minutes=CHECK_ORDERS_INTERVAL, args=[bot])
    scheduler.add_job(check_all_prices, "interval", minutes=CHECK_PRICES_INTERVAL,  args=[bot])
    return scheduler
