import asyncio
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)

from config import TOKEN, ADMIN_ID


# =========================
# BOT
# =========================

bot = Bot(token=TOKEN)
dp = Dispatcher()


# =========================
# SHOP SETTINGS
# =========================

PRODUCT_NAME = "Премиальный поводок UTTA"
PRODUCT_PRICE = 2000

COLORS = {
    "pink": "🩷 Розовый",
    "blue": "💙 Голубой",
    "green": "💚 Салатовый",
}


# =========================
# ORDER STATES
# =========================

class OrderState(StatesGroup):
    choosing_color = State()
    waiting_phone = State()
    waiting_address = State()


# =========================
# KEYBOARDS
# =========================

def main_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛍 Каталог",
                    callback_data="catalog"
                )
            ],
            [
                InlineKeyboardButton(
                    text="ℹ️ О магазине",
                    callback_data="about"
                ),
                InlineKeyboardButton(
                    text="📩 Связаться",
                    callback_data="contact"
                )
            ]
        ]
    )


def catalog_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🩷 Розовый",
                    callback_data="color:pink"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💙 Голубой",
                    callback_data="color:blue"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💚 Салатовый",
                    callback_data="color:green"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ В меню",
                    callback_data="menu"
                )
            ]
        ]
    )


def product_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛒 Оформить заказ",
                    callback_data="order"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🎨 Выбрать другой цвет",
                    callback_data="catalog"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ В меню",
                    callback_data="menu"
                )
            ]
        ]
    )


# =========================
# /START
# =========================

@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):

    # Очищаем старое состояние
    await state.clear()

    await message.answer(
        "🐶 Добро пожаловать в магазин UTTA!\n\n"
        "Премиальные аксессуары для собак.\n\n"
        "Выберите раздел:",
        reply_markup=main_menu()
    )


# =========================
# MAIN MENU
# =========================

@dp.callback_query(F.data == "menu")
async def menu(
    callback: CallbackQuery,
    state: FSMContext
):

    await state.clear()

    await callback.message.edit_text(
        "🐶 UTTA — премиальные аксессуары для собак.\n\n"
        "Выберите раздел:",
        reply_markup=main_menu()
    )

    await callback.answer()


# =========================
# CATALOG
# =========================

@dp.callback_query(F.data == "catalog")
async def catalog(
    callback: CallbackQuery,
    state: FSMContext
):

    await state.set_state(OrderState.choosing_color)

    await callback.message.edit_text(
        f"🛍 КАТАЛОГ UTTA\n\n"
        f"{PRODUCT_NAME}\n"
        f"Цена: {PRODUCT_PRICE:,} ₽\n\n"
        f"Выберите цвет:",
        reply_markup=catalog_keyboard()
    )

    await callback.answer()


# =========================
# CHOOSE COLOR
# =========================

@dp.callback_query(F.data.startswith("color:"))
async def choose_color(
    callback: CallbackQuery,
    state: FSMContext
):

    color_key = callback.data.split(":", 1)[1]
    color = COLORS.get(color_key)

    if not color:
        await callback.answer(
            "Цвет не найден",
            show_alert=True
        )
        return

    await state.update_data(color=color)

    await state.set_state(
        OrderState.choosing_color
    )

    await callback.message.edit_text(
        f"🐾 ВАШ ТОВАР\n\n"
        f"{PRODUCT_NAME}\n"
        f"Цвет: {color}\n"
        f"Цена: {PRODUCT_PRICE:,} ₽\n\n"
        f"Готовы оформить заказ?",
        reply_markup=product_keyboard()
    )

    await callback.answer()


# =========================
# START ORDER
# =========================

@dp.callback_query(F.data == "order")
async def start_order(
    callback: CallbackQuery,
    state: FSMContext
):

    data = await state.get_data()

    if not data.get("color"):
        await callback.answer(
            "Сначала выберите цвет",
            show_alert=True
        )
        return

    await state.set_state(
        OrderState.waiting_phone
    )

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="📱 Отправить номер телефона",
                    request_contact=True
                )
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await callback.message.answer(
        "🛒 Оформление заказа\n\n"
        "Нажмите кнопку ниже, чтобы отправить "
        "номер телефона.",
        reply_markup=keyboard
    )

    await callback.answer()


# =========================
# RECEIVE PHONE
# =========================

@dp.message(
    OrderState.waiting_phone,
    F.contact
)
async def receive_phone(
    message: Message,
    state: FSMContext
):

    await state.update_data(
        phone=message.contact.phone_number
    )

    await state.set_state(
        OrderState.waiting_address
    )

    await message.answer(
        "Спасибо! 👍\n\n"
        "Теперь напишите адрес доставки одним сообщением.",
        reply_markup=ReplyKeyboardRemove()
    )


# =========================
# PHONE ENTERED AS TEXT
# =========================

@dp.message(
    OrderState.waiting_phone,
    F.text
)
async def phone_text(message: Message):

    await message.answer(
        "Пожалуйста, используйте кнопку "
        "«📱 Отправить номер телефона»."
    )


# =========================
# RECEIVE ADDRESS
# =========================

@dp.message(
    OrderState.waiting_address,
    F.text
)
async def receive_address(
    message: Message,
    state: FSMContext
):

    address = message.text.strip()

    if len(address) < 5:

        await message.answer(
            "Пожалуйста, укажите полный адрес доставки."
        )

        return

    data = await state.get_data()

    username = (
        f"@{message.from_user.username}"
        if message.from_user.username
        else "без username"
    )

    order_text = (
        "🆕 НОВЫЙ ЗАКАЗ UTTA\n\n"
        f"Товар: {PRODUCT_NAME}\n"
        f"Цвет: {data.get('color', 'Не указан')}\n"
        f"Цена: {PRODUCT_PRICE:,} ₽\n\n"
        f"Клиент: {message.from_user.full_name}\n"
        f"Telegram: {username}\n"
        f"Телефон: {data.get('phone', 'Не указан')}\n"
        f"Адрес: {address}"
    )

    # Отправляем заказ администратору
    if ADMIN_ID:

        try:

            await bot.send_message(
                ADMIN_ID,
                order_text
            )

        except Exception as e:

            print(
                f"Ошибка отправки заказа админу: {e}"
            )

    await state.clear()

    await message.answer(
        "✅ Заказ принят!\n\n"
        "Мы свяжемся с вами для подтверждения "
        "и оплаты.",
        reply_markup=main_menu()
    )


# =========================
# ABOUT
# =========================

@dp.callback_query(F.data == "about")
async def about(
    callback: CallbackQuery
):

    await callback.message.edit_text(
        "🐶 О UTTA\n\n"
        "UTTA — бренд стильных аксессуаров "
        "для собак.\n\n"
        "Сейчас доступны премиальные поводки "
        "в трёх цветах.\n\n"
        "Стоимость поводка — 2 000 ₽.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🛍 Каталог",
                        callback_data="catalog"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="⬅️ В меню",
                        callback_data="menu"
                    )
                ]
            ]
        )
    )

    await callback.answer()


# =========================
# CONTACT
# =========================

@dp.callback_query(F.data == "contact")
async def contact(
    callback: CallbackQuery
):

    await callback.message.edit_text(
        "📩 Связаться с UTTA\n\n"
        "По вопросам заказа напишите нам в Telegram.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="⬅️ В меню",
                        callback_data="menu"
                    )
                ]
            ]
        )
    )

    await callback.answer()


# ==================================================
# RENDER WEB SERVER
# ==================================================
#
# Render Web Service требует открытый HTTP-порт.
# Telegram-боту порт сам по себе не нужен,
# поэтому ниже запускаем небольшой HTTP-сервер.
#
# Это позволяет оставить Render Web Service
# бесплатным и не добавлять aiohttp.
# ==================================================

async def handle_http_request(
    reader,
    writer
):

    try:

        # Читаем HTTP-запрос
        await reader.read(4096)

        response_body = (
            "UTTA Telegram Bot is running"
        ).encode()

        response = (
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Type: text/plain; charset=utf-8\r\n"
            b"Content-Length: "
            + str(len(response_body)).encode()
            + b"\r\n"
            b"Connection: close\r\n"
            b"\r\n"
            + response_body
        )

        writer.write(response)

        await writer.drain()

    except Exception as e:

        print(
            f"HTTP server error: {e}"
        )

    finally:

        writer.close()

        try:
            await writer.wait_closed()

        except Exception:
            pass


async def start_web_server():

    # Render передаёт PORT через переменную окружения
    port = int(
        os.getenv(
            "PORT",
            "10000"
        )
    )

    server = await asyncio.start_server(
        handle_http_request,
        host="0.0.0.0",
        port=port
    )

    print(
        f"HTTP server started on port {port}"
    )

    return server


# =========================
# MAIN
# =========================

async def main():

    # Запускаем HTTP-сервер для Render
    server = await start_web_server()

    try:

        print(
            "UTTA Telegram Bot starting..."
        )

        # Запускаем Telegram polling
        await dp.start_polling(bot)

    finally:

        server.close()

        await server.wait_closed()

        await bot.session.close()


# =========================
# RUN
# =========================

if __name__ == "__main__":

    try:

        asyncio.run(main())

    except KeyboardInterrupt:

        print(
            "UTTA Telegram Bot stopped."
        )
