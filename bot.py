"""
bot.py — точка входа

Запуск: python bot.py

Команды:
/start    — главное меню
/register — подключить Kaspi магазин
/status   — статус и список товаров
/help     — помощь
"""

import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, DEMO_MODE, SUPPORT_USERNAME
from storage import save_seller, get_seller
from kaspi_api import test_token, get_products
from scheduler import setup_scheduler

if not BOT_TOKEN:
    raise RuntimeError(f"BOT_TOKEN не найден! Все переменные: {list(os.environ.keys())}")

bot = Bot(token=BOT_TOKEN)
dp  = Dispatcher(storage=MemoryStorage())


# -------------------------------------------------------
# FSM — диалог регистрации
# -------------------------------------------------------

class Reg(StatesGroup):
    token     = State()
    shop_name = State()


# -------------------------------------------------------
# /start
# -------------------------------------------------------

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    seller = get_seller(message.from_user.id)
    mode   = "\n\n🔧 <i>Демо-режим — данные тестовые</i>" if DEMO_MODE else ""

    if seller:
        await message.answer(
            f"👋 С возвращением!\n\n"
            f"🏪 Магазин: <b>{seller['shop_name']}</b>\n\n"
            f"/status — статус и товары\n"
            f"/help — помощь"
            f"{mode}",
            parse_mode="HTML",
        )
    else:
        await message.answer(
            f"👋 Привет!\n\n"
            f"Я слежу за вашим магазином на Kaspi и сообщаю когда:\n\n"
            f"🛒 Пришёл новый заказ\n"
            f"⚠️ Конкурент снизил цену\n"
            f"📦 Товар заканчивается или закончился\n\n"
            f"Для подключения магазина: /register"
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
        text = (
            "🔧 <b>Демо-режим</b>\n\n"
            "Введите любое слово как токен.\n"
            "Когда переключитесь на реальный режим — введите токен из личного кабинета Kaspi."
        )
    else:
        text = (
            "📝 <b>Подключение магазина</b>\n\n"
            "Получите токен в личном кабинете Kaspi:\n\n"
            "1. kaspi.kz/merchants\n"
            "2. Настройки → API интеграция\n"
            "3. Нажмите «Сгенерировать токен»\n"
            "4. Скопируйте и отправьте сюда"
        )

    await message.answer(text, parse_mode="HTML")
    await state.set_state(Reg.token)


@dp.message(Reg.token)
async def process_token(message: types.Message, state: FSMContext):
    token = message.text.strip()

    await message.answer("⏳ Проверяю токен...")

    if not await test_token(token):
        await message.answer(
            f"❌ Токен не подошёл. Проверьте и попробуйте снова.\n"
            f"Если проблема остаётся: {SUPPORT_USERNAME}"
        )
        return

    await state.update_data(token=token)
    await state.set_state(Reg.shop_name)
    await message.answer(
        "✅ Токен принят!\n\n"
        "Теперь введите <b>название вашего магазина на Kaspi</b>\n"
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
        f"Теперь вы будете получать уведомления о заказах и ценах конкурентов.\n\n"
        f"/status — посмотреть товары",
        parse_mode="HTML",
    )


# -------------------------------------------------------
# /status
# -------------------------------------------------------

@dp.message(Command("status"))
async def cmd_status(message: types.Message):
    seller = get_seller(message.from_user.id)

    if not seller:
        await message.answer("Вы не зарегистрированы. Используйте /register")
        return

    await message.answer("⏳ Загружаю данные...")

    products     = await get_products(seller["kaspi_token"])
    out_of_stock = [p for p in products if p.get("quantity", 0) == 0]
    low_stock    = [p for p in products if 0 < p.get("quantity", 0) <= 5]

    # Итоговая строка по остаткам
    stock_line = f"📦 Товаров: <b>{len(products)}</b>"
    if out_of_stock:
        stock_line += f"\n🚨 Нет в наличии: <b>{len(out_of_stock)}</b>"
    if low_stock:
        stock_line += f"\n⚠️ Заканчиваются: <b>{len(low_stock)}</b>"

    await message.answer(
        f"📊 <b>Статус магазина</b>\n\n"
        f"🏪 {seller['shop_name']}\n"
        f"{stock_line}\n\n"
        f"Заказы проверяются каждые 2 минуты\n"
        f"Цены конкурентов — каждые 30 минут\n"
        f"Остатки — каждый час",
        parse_mode="HTML",
    )

    # Если есть проблемные товары — показываем список
    if out_of_stock or low_stock:
        lines = []
        for p in out_of_stock[:5]:
            lines.append(f"🚨 {p['name']} — нет в наличии")
        for p in low_stock[:5]:
            lines.append(f"⚠️ {p['name']} — осталось {p['quantity']} шт")

        await message.answer(
            "<b>Требуют внимания:</b>\n\n" + "\n".join(lines),
            parse_mode="HTML",
        )


# -------------------------------------------------------
# /help
# -------------------------------------------------------

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "❓ <b>Помощь</b>\n\n"
        "/start — главное меню\n"
        "/register — подключить магазин\n"
        "/status — статус и товары\n\n"
        f"По вопросам: {SUPPORT_USERNAME}",
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
