"""
scheduler.py

Три фоновые задачи:
1. Проверка новых заказов
2. Мониторинг цен конкурентов
3. Проверка остатков товаров
"""

import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot

from config import CHECK_ORDERS_INTERVAL, CHECK_PRICES_INTERVAL, CHECK_STOCK_INTERVAL, LOW_STOCK_THRESHOLD
from storage import get_all_sellers, is_order_seen, mark_order_seen, get_last_competitor_price, save_competitor_price
from kaspi_api import get_new_orders, get_products
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
    try:
        products   = await get_products(seller["kaspi_token"])
        shop_name  = seller.get("shop_name", "")

        for product in products:
            if not product.get("url"):
                continue

            my_price = product.get("price", 0)
            if my_price == 0:
                continue

            min_price = await get_min_competitor_price(
                product["url"],
                my_price=my_price,
                my_shop_name=shop_name,
            )

            if min_price is None:
                continue

            # Уведомляем только если конкурент дешевле
            # И только если цена изменилась с прошлого раза (не спамим)
            if min_price < my_price:
                last = get_last_competitor_price(seller["telegram_id"], product["id"])
                if last != min_price:
                    save_competitor_price(seller["telegram_id"], product["id"], min_price)
                    await _send_price_alert(bot, seller["telegram_id"], product, my_price, min_price)

            await asyncio.sleep(1)  # Пауза между товарами

    except Exception as e:
        print(f"[scheduler] Цены {seller['telegram_id']}: {e}")


async def check_all_prices(bot: Bot):
    print("[scheduler] Проверяем цены конкурентов...")
    for seller in get_all_sellers():
        await _check_prices(bot, seller)
        await asyncio.sleep(2)


# -------------------------------------------------------
# Остатки
# -------------------------------------------------------

async def _check_stock(bot: Bot, seller: dict):
    try:
        products = await get_products(seller["kaspi_token"])
        for product in products:
            qty  = product.get("quantity", 0)
            name = product.get("name", "Товар")

            if qty == 0:
                await bot.send_message(
                    seller["telegram_id"],
                    f"🚨 <b>Товар закончился!</b>\n\n"
                    f"📦 {name}\n\n"
                    f"Срочно обновите остатки — иначе штраф от Kaspi.",
                    parse_mode="HTML",
                )
            elif qty <= LOW_STOCK_THRESHOLD:
                await bot.send_message(
                    seller["telegram_id"],
                    f"⚠️ <b>Товар заканчивается</b>\n\n"
                    f"📦 {name}\n"
                    f"Осталось: <b>{qty} шт</b>",
                    parse_mode="HTML",
                )
    except Exception as e:
        print(f"[scheduler] Остатки {seller['telegram_id']}: {e}")


async def check_all_stock(bot: Bot):
    print("[scheduler] Проверяем остатки...")
    tasks = [_check_stock(bot, s) for s in get_all_sellers()]
    await asyncio.gather(*tasks, return_exceptions=True)


# -------------------------------------------------------
# Уведомления
# -------------------------------------------------------

async def _send_order(bot: Bot, telegram_id: int, order: dict):
    total = order.get("totalPrice", 0)
    await bot.send_message(
        telegram_id,
        f"🛒 <b>Новый заказ!</b>\n\n"
        f"📦 <b>Товар:</b> {order.get('product_name', 'Товар')}\n"
        f"🔢 <b>Количество:</b> {order.get('quantity', 1)} шт\n"
        f"💰 <b>Сумма:</b> {total:,} ₸\n"
        f"👤 <b>Покупатель:</b> {order.get('customer_name', 'скрыто')}\n"
        f"📍 <b>Адрес:</b> {order.get('delivery_address', 'не указан')}\n\n"
        f"🔖 Номер: <code>{order.get('id', '—')}</code>",
        parse_mode="HTML",
    )


async def _send_price_alert(bot: Bot, telegram_id: int, product: dict, my_price: int, competitor_price: int):
    diff = my_price - competitor_price
    await bot.send_message(
        telegram_id,
        f"⚠️ <b>Конкурент дешевле!</b>\n\n"
        f"📦 {product.get('name', 'Товар')}\n\n"
        f"💰 Ваша цена:   <b>{my_price:,} ₸</b>\n"
        f"🔻 Конкурент:  <b>{competitor_price:,} ₸</b>\n"
        f"📉 Разница:     <b>{diff:,} ₸</b>",
        parse_mode="HTML",
    )


# -------------------------------------------------------
# Запуск планировщика
# -------------------------------------------------------

def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="Asia/Almaty")

    scheduler.add_job(check_all_orders, "interval", minutes=CHECK_ORDERS_INTERVAL, args=[bot])
    scheduler.add_job(check_all_prices, "interval", minutes=CHECK_PRICES_INTERVAL, args=[bot])
    scheduler.add_job(check_all_stock,  "interval", minutes=CHECK_STOCK_INTERVAL,  args=[bot])

    return scheduler
