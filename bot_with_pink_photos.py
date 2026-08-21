import asyncio
import os
from datetime import datetime

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


# ============================================================
# BOT
# ============================================================

bot = Bot(token=TOKEN)
dp = Dispatcher()


# ============================================================
# SHOP SETTINGS
# ============================================================

PRODUCT_NAME = "Премиальный поводок UTTA"
PRODUCT_PRICE = 2000

COLORS = {
    "pink": "🩷 Розовый",
    "blue": "💙 Голубой",
    "green": "💚 Салатовый",
}


# ============================================================
# ORDER STATES
# ============================================================

class OrderState(StatesGroup):
    choosing_color = State()
    waiting_phone = State()
    waiting_address = State()
    confirming = State()


# ============================================================
# MAIN MENU
# ============================================================

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


# ============================================================
# CATALOG
# ============================================================

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


# ============================================================
# PRODUCT
# ============================================================

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


# ============================================================
# CONFIRM ORDER KEYBOARD
# ============================================================

def confirm_order_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить заказ",
                    callback_data="confirm_order"
                )
            ],
            [
                InlineKeyboardButton(
                    text="✏️ Изменить данные",
                    callback_data="change_order"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отменить",
                    callback_data="cancel_order"
                )
            ]
        ]
    )


# ============================================================
# ADMIN KEYBOARD
# ============================================================

def admin_order_keyboard(order_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Принять заказ",
                    callback_data=f"admin_accept:{order_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отклонить заказ",
                    callback_data=f"admin_reject:{order_id}"
                )
            ]
        ]
    )


# ============================================================
# START
# ============================================================

@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):

    await state.clear()

    await message.answer(
        "🐶 <b>Добро пожаловать в UTTA!</b>\n\n"
        "Премиальные аксессуары для собак.\n\n"
        "Выберите нужный раздел:",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )


# ============================================================
# MENU
# ============================================================

@dp.callback_query(F.data == "menu")
async def menu(
    callback: CallbackQuery,
    state: FSMContext
):

    await state.clear()

    await callback.message.edit_text(
        "🐶 <b>UTTA</b>\n\n"
        "Премиальные аксессуары для собак.\n\n"
        "Выберите нужный раздел:",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )

    await callback.answer()


# ============================================================
# CATALOG
# ============================================================

@dp.callback_query(F.data == "catalog")
async def catalog(
    callback: CallbackQuery,
    state: FSMContext
):

    await state.set_state(OrderState.choosing_color)

    await callback.message.edit_text(
        "🛍 <b>КАТАЛОГ UTTA</b>\n\n"
        f"<b>{PRODUCT_NAME}</b>\n"
        f"💰 Цена: <b>{PRODUCT_PRICE:,} ₽</b>\n\n"
        "Выберите цвет:".replace(",", " "),
        reply_markup=catalog_keyboard(),
        parse_mode="HTML"
    )

    await callback.answer()


# ============================================================
# COLOR
# ============================================================

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

    await state.update_data(
        color=color,
        color_key=color_key
    )

    await callback.message.edit_text(
        "🐾 <b>ВАШ ТОВАР</b>\n\n"
        f"🦮 {PRODUCT_NAME}\n"
        f"🎨 Цвет: <b>{color}</b>\n"
        f"💰 Цена: <b>{PRODUCT_PRICE:,} ₽</b>\n\n"
        "Готовы оформить заказ?",
        reply_markup=product_keyboard(),
        parse_mode="HTML"
    )

    await callback.answer()


# ============================================================
# START ORDER
# ============================================================

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

    await state.set_state(OrderState.waiting_phone)

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
        "🛒 <b>ОФОРМЛЕНИЕ ЗАКАЗА</b>\n\n"
        "Нажмите кнопку ниже, чтобы отправить "
        "номер телефона.",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

    await callback.answer()


# ============================================================
# PHONE
# ============================================================

@dp.message(
    OrderState.waiting_phone,
    F.contact
)
async def receive_phone(
    message: Message,
    state: FSMContext
):

    phone = message.contact.phone_number

    await state.update_data(phone=phone)

    await state.set_state(
        OrderState.waiting_address
    )

    await message.answer(
        "✅ Номер телефона получен.\n\n"
        "📍 Теперь напишите <b>адрес доставки</b> "
        "одним сообщением.\n\n"
        "Например:\n"
        "Москва, ул. Ленина, дом 10, кв. 25",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML"
    )


# ============================================================
# PHONE TEXT
# ============================================================

@dp.message(
    OrderState.waiting_phone,
    F.text
)
async def phone_text(message: Message):

    await message.answer(
        "📱 Пожалуйста, нажмите кнопку "
        "«Отправить номер телефона»."
    )


# ============================================================
# ADDRESS
# ============================================================

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
            "⚠️ Адрес слишком короткий.\n\n"
            "Пожалуйста, укажите полный адрес доставки."
        )
        return

    await state.update_data(
        address=address
    )

    data = await state.get_data()

    await state.set_state(
        OrderState.confirming
    )

    await message.answer(
        "📋 <b>ПРОВЕРЬТЕ ЗАКАЗ</b>\n\n"
        f"🦮 Товар: <b>{PRODUCT_NAME}</b>\n"
        f"🎨 Цвет: <b>{data.get('color')}</b>\n"
        f"💰 Цена: <b>{PRODUCT_PRICE:,} ₽</b>\n\n"
        f"📱 Телефон: <b>{data.get('phone')}</b>\n"
        f"📍 Адрес: <b>{address}</b>\n\n"
        "Всё верно?",
        reply_markup=confirm_order_keyboard(),
        parse_mode="HTML"
    )


# ============================================================
# CONFIRM ORDER
# ============================================================

@dp.callback_query(F.data == "confirm_order")
async def confirm_order(
    callback: CallbackQuery,
    state: FSMContext
):

    data = await state.get_data()

    if not data.get("color"):
        await callback.answer(
            "Данные заказа потеряны. Начните заново.",
            show_alert=True
        )
        await state.clear()
        return

    if not data.get("phone"):
        await callback.answer(
            "Не указан телефон.",
            show_alert=True
        )
        return

    if not data.get("address"):
        await callback.answer(
            "Не указан адрес.",
            show_alert=True
        )
        return

    # Генерируем номер заказа
    order_id = datetime.now().strftime(
        "%Y%m%d%H%M%S"
    )

    username = (
        f"@{callback.from_user.username}"
        if callback.from_user.username
        else "нет username"
    )

    customer_name = callback.from_user.full_name

    order_text = (
        "🆕 <b>НОВЫЙ ЗАКАЗ UTTA</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"🔢 Заказ: <b>#{order_id}</b>\n\n"
        f"🦮 Товар: <b>{PRODUCT_NAME}</b>\n"
        f"🎨 Цвет: <b>{data.get('color')}</b>\n"
        f"💰 Сумма: <b>{PRODUCT_PRICE:,} ₽</b>\n\n"
        "👤 <b>КЛИЕНТ</b>\n"
        f"Имя: {customer_name}\n"
        f"Telegram: {username}\n"
        f"ID: <code>{callback.from_user.id}</code>\n"
        f"📱 Телефон: {data.get('phone')}\n"
        f"📍 Адрес: {data.get('address')}\n"
    )

    # Отправляем заказ администратору
    if ADMIN_ID:

        try:

            await bot.send_message(
                ADMIN_ID,
                order_text,
                reply_markup=admin_order_keyboard(
                    order_id
                ),
                parse_mode="HTML"
            )

        except Exception as e:

            print(
                f"Ошибка отправки заказа админу: {e}"
            )

            await callback.answer(
                "Не удалось отправить заказ. "
                "Попробуйте ещё раз.",
                show_alert=True
            )
            return

    else:

        print(
            "ADMIN_ID не установлен!"
        )

    await state.clear()

    await callback.message.edit_text(
        "🎉 <b>ЗАКАЗ ПРИНЯТ!</b>\n\n"
        f"Номер заказа: <b>#{order_id}</b>\n\n"
        f"🦮 {PRODUCT_NAME}\n"
        f"🎨 {data.get('color')}\n"
        f"💰 {PRODUCT_PRICE:,} ₽\n\n"
        "Мы свяжемся с вами для подтверждения "
        "заказа и оплаты.\n\n"
        "Спасибо, что выбираете UTTA 🐶❤️",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )

    await callback.answer(
        "Заказ отправлен!"
    )


# ============================================================
# CHANGE ORDER
# ============================================================

@dp.callback_query(F.data == "change_order")
async def change_order(
    callback: CallbackQuery,
    state: FSMContext
):

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
        "✏️ Давайте изменим данные заказа.\n\n"
        "Сначала отправьте номер телефона.",
        reply_markup=keyboard
    )

    await callback.answer()


# ============================================================
# CANCEL ORDER
# ============================================================

@dp.callback_query(F.data == "cancel_order")
async def cancel_order(
    callback: CallbackQuery,
    state: FSMContext
):

    await state.clear()

    await callback.message.edit_text(
        "❌ <b>Заказ отменён.</b>\n\n"
        "Вы можете вернуться в каталог в любое время.",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )

    await callback.answer()


# ============================================================
# ADMIN — ACCEPT
# ============================================================

@dp.callback_query(F.data.startswith("admin_accept:"))
async def admin_accept(
    callback: CallbackQuery
):

    if callback.from_user.id != ADMIN_ID:
        await callback.answer(
            "Нет доступа.",
            show_alert=True
        )
        return

    order_id = callback.data.split(
        ":", 1
    )[1]

    await callback.message.edit_reply_markup(
        reply_markup=None
    )

    await callback.message.answer(
        f"✅ <b>Заказ #{order_id} принят.</b>",
        parse_mode="HTML"
    )

    await callback.answer(
        "Заказ принят"
    )


# ============================================================
# ADMIN — REJECT
# ============================================================

@dp.callback_query(F.data.startswith("admin_reject:"))
async def admin_reject(
    callback: CallbackQuery
):

    if callback.from_user.id != ADMIN_ID:
        await callback.answer(
            "Нет доступа.",
            show_alert=True
        )
        return

    order_id = callback.data.split(
        ":", 1
    )[1]

    await callback.message.edit_reply_markup(
        reply_markup=None
    )

    await callback.message.answer(
        f"❌ <b>Заказ #{order_id} отклонён.</b>",
        parse_mode="HTML"
    )

    await callback.answer(
        "Заказ отклонён"
    )


# ============================================================
# ABOUT
# ============================================================

@dp.callback_query(F.data == "about")
async def about(
    callback: CallbackQuery
):

    await callback.message.edit_text(
        "🐶 <b>О UTTA</b>\n\n"
        "UTTA — бренд стильных аксессуаров "
        "для собак.\n\n"
        "Мы создаём красивые и удобные аксессуары "
        "для прогулок.\n\n"
        "🦮 Сейчас в магазине доступны "
        "премиальные поводки.\n\n"
        "🎨 Цвета:\n"
        "🩷 Розовый\n"
        "💙 Голубой\n"
        "💚 Салатовый\n\n"
        "💰 Стоимость — <b>2 000 ₽</b>",
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
        ),
        parse_mode="HTML"
    )

    await callback.answer()


# ============================================================
# CONTACT
# ============================================================

@dp.callback_query(F.data == "contact")
async def contact(
    callback: CallbackQuery
):

    await callback.message.edit_text(
        "📩 <b>СВЯЗАТЬСЯ С UTTA</b>\n\n"
        "Если у вас есть вопрос по товару или заказу — "
        "напишите нам в Telegram.\n\n"
        "Мы обязательно ответим.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="⬅️ В меню",
                        callback_data="menu"
                    )
                ]
            ]
        ),
        parse_mode="HTML"
    )

    await callback.answer()


# ============================================================
# RENDER HTTP SERVER
# ============================================================

async def handle_http_request(
    reader,
    writer
):

    try:

        await reader.read(4096)

        body = (
            "UTTA Telegram Bot is running"
        ).encode("utf-8")

        response = (
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Type: text/plain; "
            b"charset=utf-8\r\n"
            b"Content-Length: "
            + str(len(body)).encode()
            + b"\r\n"
            b"Connection: close\r\n"
            b"\r\n"
            + body
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


# ============================================================
# START WEB SERVER
# ============================================================

async def start_web_server():

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


# ============================================================
# MAIN
# ============================================================

async def main():

    server = await start_web_server()

    try:

        print(
            "================================"
        )

        print(
            "UTTA BOT STARTING..."
        )

        print(
            "================================"
        )

        await dp.start_polling(
            bot
        )

    finally:

        server.close()

        await server.wait_closed()

        await bot.session.close()


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    asyncio.run(main())
