"""
bot.py — точка входа

Команды:
/start       — главное меню
/register    — подключить Kaspi магазин
/status      — статус
/addproduct  — добавить товар для мониторинга цен
/myproducts  — список товаров на мониторинге
/help        — помощь
"""

import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, DEMO_MODE, SUPPORT_USERNAME
from storage import save_seller, get_seller, get_products_for_seller, add_product, remove_product
from kaspi_api import test_token
from scheduler import setup_scheduler

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не найден!")

bot = Bot(token=BOT_TOKEN)
dp  = Dispatcher(storage=MemoryStorage())


# -------------------------------------------------------
# FSM состояния
# -------------------------------------------------------

class Reg(StatesGroup):
    token     = State()
    shop_name = State()

class AddProduct(StatesGroup):
    url  = State()
    name = State()


# -------------------------------------------------------
# /start
# -------------------------------------------------------

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    seller = get_seller(message.from_user.id)
    mode   = "\n\n🔧 <i>Демо-режим</i>" if DEMO_MODE else ""

    if seller:
        await message.answer(
            f"👋 С возвращением!\n\n"
            f"🏪 Магазин: <b>{seller['shop_name']}</b>\n\n"
            f"/status — статус\n"
            f"/addproduct — добавить товар для мониторинга цен\n"
            f"/myproducts — мои товары на мониторинге\n"
            f"/help — помощь"
            f"{mode}",
            parse_mode="HTML",
        )
    else:
        await message.answer(
            f"👋 Привет!\n\n"
            f"Я слежу за вашим магазином на Kaspi:\n\n"
            f"🛒 Уведомления о новых заказах\n"
            f"⚠️ Мониторинг цен конкурентов\n\n"
            f"Для подключения: /register"
            f"{mode}",
            parse_mode="HTML",
        )


# -------------------------------------------------------
# /register
# -------------------------------------------------------

@dp.message(Command("register"))
async def cmd_register(message: types.Message, state: FSMContext):
    await state.clear()
    if DEMO_MODE:
        text = "🔧 <b>Демо-режим</b>\n\nВведите любое слово как токен."
    else:
        text = (
            "📝 <b>Подключение магазина</b>\n\n"
            "Получите токен:\n"
            "1. kaspi.kz/shop/info/merchant/\n"
            "2. Интеграция → API\n"
            "3. Скопируйте токен и отправьте сюда"
        )
    await message.answer(text, parse_mode="HTML")
    await state.set_state(Reg.token)


@dp.message(Reg.token)
async def process_token(message: types.Message, state: FSMContext):
    token = message.text.strip()
    await message.answer("⏳ Проверяю токен...")
    if not await test_token(token):
        await message.answer(f"❌ Токен не подошёл.\n{SUPPORT_USERNAME}")
        return
    await state.update_data(token=token)
    await state.set_state(Reg.shop_name)
    await message.answer(
        "✅ Токен принят!\n\n"
        "Введите <b>название магазина на Kaspi</b>\n"
        "<i>Точно как написано в профиле продавца</i>",
        parse_mode="HTML",
    )


@dp.message(Reg.shop_name)
async def process_shop_name(message: types.Message, state: FSMContext):
    data      = await state.get_data()
    shop_name = message.text.strip()
    save_seller(message.from_user.id, data["token"], shop_name)
    await state.clear()
    await message.answer(
        f"🎉 <b>Готово! Магазин подключён.</b>\n\n"
        f"🏪 {shop_name}\n\n"
        f"Теперь буду уведомлять о новых заказах.\n\n"
        f"Добавьте товары для мониторинга цен: /addproduct",
        parse_mode="HTML",
    )


# -------------------------------------------------------
# /status
# -------------------------------------------------------

@dp.message(Command("status"))
async def cmd_status(message: types.Message):
    seller = get_seller(message.from_user.id)
    if not seller:
        await message.answer("Не зарегистрированы. /register")
        return

    products = get_products_for_seller(message.from_user.id)
    await message.answer(
        f"📊 <b>Статус магазина</b>\n\n"
        f"🏪 {seller['shop_name']}\n"
        f"📦 Товаров на мониторинге: <b>{len(products)}</b>\n\n"
        f"Заказы проверяются каждые 2 минуты\n"
        f"Цены конкурентов — каждые 30 минут",
        parse_mode="HTML",
    )


# -------------------------------------------------------
# /addproduct — добавить товар для мониторинга
# -------------------------------------------------------

@dp.message(Command("addproduct"))
async def cmd_addproduct(message: types.Message, state: FSMContext):
    seller = get_seller(message.from_user.id)
    if not seller:
        await message.answer("Не зарегистрированы. /register")
        return

    await message.answer(
        "📦 <b>Добавление товара для мониторинга цен</b>\n\n"
        "Пришлите ссылку на товар с Kaspi\n\n"
        "<i>Пример:\n"
        "https://kaspi.kz/shop/p/apple-iphone-15-pro-128gb-chernyj-titanium-111111111/</i>",
        parse_mode="HTML",
    )
    await state.set_state(AddProduct.url)


@dp.message(AddProduct.url)
async def process_product_url(message: types.Message, state: FSMContext):
    url = message.text.strip()

    if "kaspi.kz" not in url:
        await message.answer("❌ Это не ссылка на Kaspi. Попробуйте снова.")
        return

    await state.update_data(url=url)
    await state.set_state(AddProduct.name)
    await message.answer(
        "Введите короткое название товара\n"
        "<i>Например: Чехол iPhone 15 Pro чёрный</i>",
        parse_mode="HTML",
    )


@dp.message(AddProduct.name)
async def process_product_name(message: types.Message, state: FSMContext):
    data = await state.get_data()
    name = message.text.strip()
    url  = data["url"]

    added = add_product(message.from_user.id, url, name)
    await state.clear()

    if added:
        await message.answer(
            f"✅ <b>Товар добавлен!</b>\n\n"
            f"📦 {name}\n\n"
            f"Буду проверять цены конкурентов каждые 30 минут.\n"
            f"Список товаров: /myproducts",
            parse_mode="HTML",
        )
    else:
        await message.answer("Этот товар уже есть в списке мониторинга.")


# -------------------------------------------------------
# /myproducts — список товаров на мониторинге
# -------------------------------------------------------

@dp.message(Command("myproducts"))
async def cmd_myproducts(message: types.Message):
    seller = get_seller(message.from_user.id)
    if not seller:
        await message.answer("Не зарегистрированы. /register")
        return

    products = get_products_for_seller(message.from_user.id)

    if not products:
        await message.answer(
            "Товаров на мониторинге нет.\n\n"
            "Добавьте первый: /addproduct"
        )
        return

    lines = []
    for i, p in enumerate(products, 1):
        last = p.get("last_price")
        price_str = f"{last:,} ₸" if last else "ещё не проверялась"
        lines.append(f"{i}. <b>{p['name']}</b>\n   Мин. цена конкурента: {price_str}")

    await message.answer(
        f"📦 <b>Товары на мониторинге</b>\n\n" + "\n\n".join(lines) + "\n\n"
        f"Чтобы удалить товар — /removeproduct",
        parse_mode="HTML",
    )


# -------------------------------------------------------
# /removeproduct — удалить товар
# -------------------------------------------------------

@dp.message(Command("removeproduct"))
async def cmd_removeproduct(message: types.Message):
    products = get_products_for_seller(message.from_user.id)

    if not products:
        await message.answer("Список мониторинга пуст.")
        return

    lines = [f"{i}. {p['name']}" for i, p in enumerate(products, 1)]
    await message.answer(
        "Какой товар удалить? Напишите номер:\n\n" + "\n".join(lines)
    )


@dp.message(lambda m: m.text and m.text.isdigit())
async def process_remove_number(message: types.Message):
    products = get_products_for_seller(message.from_user.id)
    index    = int(message.text) - 1

    if not products or index < 0 or index >= len(products):
        return

    removed = remove_product(message.from_user.id, index)
    if removed:
        await message.answer(f"✅ Удалён: {removed['name']}")


# -------------------------------------------------------
# /help
# -------------------------------------------------------

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "❓ <b>Команды</b>\n\n"
        "/register — подключить магазин\n"
        "/status — статус\n"
        "/addproduct — добавить товар для мониторинга цен\n"
        "/myproducts — мои товары на мониторинге\n"
        "/removeproduct — удалить товар\n\n"
        f"Поддержка: {SUPPORT_USERNAME}",
        parse_mode="HTML",
    )


# -------------------------------------------------------
# Запуск
# -------------------------------------------------------

async def main():
    print("=" * 45)
    print("Kaspi Bot")
    print(f"Режим: {'🔧 ДЕМО' if DEMO_MODE else '🟢 РЕАЛЬНЫЙ'}")
    print("=" * 45)

    scheduler = setup_scheduler(bot)
    scheduler.start()
    print("Планировщик запущен")
    print("Бот слушает сообщения...\n")

    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
