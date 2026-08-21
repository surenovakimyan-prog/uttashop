import html
import logging
import os
import secrets
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor

from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup


# ============================================================
# CONFIG
# ============================================================

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID_RAW = os.getenv("ADMIN_ID")
DATABASE_URL = os.getenv("DATABASE_URL")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

if not ADMIN_ID_RAW:
    raise RuntimeError("ADMIN_ID is not set")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")


try:
    ADMIN_ID = int(ADMIN_ID_RAW)
except ValueError:
    raise RuntimeError("ADMIN_ID must be a number")


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


# ============================================================
# BOT
# ============================================================

bot = Bot(token=TOKEN)

storage = MemoryStorage()

dp = Dispatcher(
    bot,
    storage=storage
)


# ============================================================
# SHOP
# ============================================================

SHOP_NAME = "UTTA"

PRODUCT_NAME = "Премиальный поводок UTTA"

PRICE = 2000

COLORS = {
    "pink": "💗 Розовый",
    "blue": "💙 Голубой",
    "green": "💚 Салатовый",
}


# ============================================================
# DATABASE
# ============================================================

def get_connection():
    return psycopg2.connect(DATABASE_URL)


def init_database():
    connection = get_connection()

    try:
        with connection.cursor() as cursor:

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS orders (
                    id TEXT PRIMARY KEY,
                    client_id BIGINT NOT NULL,
                    client_name TEXT,
                    username TEXT,
                    phone TEXT,
                    address TEXT,
                    color TEXT,
                    product TEXT,
                    price INTEGER,
                    status TEXT NOT NULL DEFAULT 'new',
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            connection.commit()

    finally:
        connection.close()

    logger.info("Database initialized")


def save_order(order):
    connection = get_connection()

    try:
        with connection.cursor() as cursor:

            cursor.execute(
                """
                INSERT INTO orders (
                    id,
                    client_id,
                    client_name,
                    username,
                    phone,
                    address,
                    color,
                    product,
                    price,
                    status,
                    created_at
                )
                VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s
                )
                """,
                (
                    order["id"],
                    order["client_id"],
                    order["client_name"],
                    order["username"],
                    order["phone"],
                    order["address"],
                    order["color"],
                    order["product"],
                    order["price"],
                    order["status"],
                    order["created_at"],
                )
            )

            connection.commit()

    finally:
        connection.close()


def get_order(order_id):
    connection = get_connection()

    try:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:

            cursor.execute(
                """
                SELECT *
                FROM orders
                WHERE id = %s
                """,
                (order_id,)
            )

            return cursor.fetchone()

    finally:
        connection.close()


def update_order_status(order_id, status):
    connection = get_connection()

    try:
        with connection.cursor() as cursor:

            cursor.execute(
                """
                UPDATE orders
                SET status = %s
                WHERE id = %s
                """,
                (status, order_id)
            )

            connection.commit()

    finally:
        connection.close()


def get_user_orders(client_id):
    connection = get_connection()

    try:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:

            cursor.execute(
                """
                SELECT *
                FROM orders
                WHERE client_id = %s
                ORDER BY created_at DESC
                LIMIT 20
                """,
                (client_id,)
            )

            return cursor.fetchall()

    finally:
        connection.close()


def get_recent_orders(limit=20):
    connection = get_connection()

    try:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:

            cursor.execute(
                """
                SELECT *
                FROM orders
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (limit,)
            )

            return cursor.fetchall()

    finally:
        connection.close()


def generate_order_id():

    while True:

        order_id = secrets.token_hex(4).upper()

        if not get_order(order_id):
            return order_id


# ============================================================
# FSM
# ============================================================

class OrderForm(StatesGroup):

    waiting_for_phone = State()

    waiting_for_address = State()


# ============================================================
# KEYBOARDS
# ============================================================

def main_keyboard():

    keyboard = ReplyKeyboardMarkup(
        resize_keyboard=True
    )

    keyboard.row(
        KeyboardButton("🛍 Каталог")
    )

    keyboard.row(
        KeyboardButton("ℹ️ О магазине"),
        KeyboardButton("📩 Связаться")
    )

    return keyboard


def color_keyboard():

    keyboard = InlineKeyboardMarkup(row_width=1)

    keyboard.add(
        InlineKeyboardButton(
            "💗 Розовый",
            callback_data="color:pink"
        )
    )

    keyboard.add(
        InlineKeyboardButton(
            "💙 Голубой",
            callback_data="color:blue"
        )
    )

    keyboard.add(
        InlineKeyboardButton(
            "💚 Салатовый",
            callback_data="color:green"
        )
    )

    keyboard.add(
        InlineKeyboardButton(
            "❌ Отмена",
            callback_data="cancel_order"
        )
    )

    return keyboard


def admin_order_keyboard(order_id):

    keyboard = InlineKeyboardMarkup(row_width=2)

    keyboard.add(
        InlineKeyboardButton(
            "✅ Принять",
            callback_data=f"accept:{order_id}"
        ),
        InlineKeyboardButton(
            "❌ Отклонить",
            callback_data=f"reject:{order_id}"
        )
    )

    return keyboard


def cancel_keyboard():

    keyboard = ReplyKeyboardMarkup(
        resize_keyboard=True
    )

    keyboard.add(
        KeyboardButton("❌ Отмена")
    )

    return keyboard


def phone_keyboard():

    keyboard = ReplyKeyboardMarkup(
        resize_keyboard=True,
        one_time_keyboard=True
    )

    keyboard.add(
        KeyboardButton(
            "📱 Отправить телефон",
            request_contact=True
        )
    )

    keyboard.add(
        KeyboardButton("❌ Отмена")
    )

    return keyboard


# ============================================================
# HELPERS
# ============================================================

def safe(value):

    return html.escape(str(value))


def user_name(user):

    if user.full_name:
        return user.full_name

    if user.username:
        return f"@{user.username}"

    return "Клиент"


def username(user):

    if user.username:
        return f"@{user.username}"

    return "не указан"


def status_text(status):

    statuses = {
        "new": "🆕 Новый",
        "accepted": "✅ Принят",
        "rejected": "❌ Отклонён",
        "paid": "💳 Оплачен",
        "shipped": "📦 Отправлен",
        "completed": "🎉 Завершён",
    }

    return statuses.get(
        status,
        status
    )


# ============================================================
# START
# ============================================================

@dp.message_handler(
    commands=["start"],
    state="*"
)
async def start_command(
    message: types.Message,
    state: FSMContext
):

    await state.finish()

    text = (
        "🐾 <b>Добро пожаловать в UTTA!</b>\n\n"
        "Премиальные аксессуары для собак.\n\n"
        "🦮 Сейчас в магазине:\n"
        f"<b>{PRODUCT_NAME}</b>\n"
        f"💰 Цена: <b>{PRICE:,} ₽</b>\n\n"
        "Выберите действие ниже 👇"
    ).replace(",", " ")

    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=main_keyboard()
    )


# ============================================================
# CATALOG
# ============================================================

@dp.message_handler(
    lambda message: message.text == "🛍 Каталог",
    state="*"
)
async def catalog(
    message: types.Message,
    state: FSMContext
):

    await state.finish()

    text = (
        "🛍 <b>Каталог UTTA</b>\n\n"
        f"🐾 <b>{PRODUCT_NAME}</b>\n\n"
        "Стильный премиальный поводок "
        "для маленьких и средних собак.\n\n"
        "💰 Цена: <b>2 000 ₽</b>\n\n"
        "🎨 Доступные цвета:\n"
        "💗 Розовый\n"
        "💙 Голубой\n"
        "💚 Салатовый\n\n"
        "Выберите цвет:"
    )

    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=color_keyboard()
    )


# ============================================================
# ABOUT
# ============================================================

@dp.message_handler(
    lambda message: message.text == "ℹ️ О магазине",
    state="*"
)
async def about_shop(
    message: types.Message,
    state: FSMContext
):

    await state.finish()

    text = (
        "ℹ️ <b>О магазине UTTA</b>\n\n"
        "UTTA — премиальные аксессуары "
        "для собак. 🐾\n\n"
        "Мы создаём стильные и удобные "
        "аксессуары для маленьких и средних собак.\n\n"
        f"🐾 Товар: <b>{PRODUCT_NAME}</b>\n"
        "🎨 Цвета: розовый, голубой, салатовый\n"
        "💰 Цена: <b>2 000 ₽</b>\n\n"
        "Спасибо, что выбираете UTTA ❤️"
    )

    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=main_keyboard()
    )


# ============================================================
# CONTACT
# ============================================================

@dp.message_handler(
    lambda message: message.text == "📩 Связаться",
    state="*"
)
async def contact_shop(
    message: types.Message,
    state: FSMContext
):

    await state.finish()

    text = (
        "📩 <b>Связаться с UTTA</b>\n\n"
        "По вопросам заказа, оплаты и доставки "
        "напишите администратору магазина.\n\n"
        "Мы обязательно ответим вам."
    )

    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=main_keyboard()
    )


# ============================================================
# COLOR
# ============================================================

@dp.callback_query_handler(
    lambda call: call.data.startswith("color:")
)
async def choose_color(
    call: types.CallbackQuery,
    state: FSMContext
):

    color_code = call.data.split(":", 1)[1]

    if color_code not in COLORS:

        await call.answer(
            "Неизвестный цвет",
            show_alert=True
        )

        return

    color_name = COLORS[color_code]

    await state.update_data(
        color_code=color_code,
        color_name=color_name
    )

    await call.answer(
        f"Выбран: {color_name}"
    )

    try:

        await call.message.edit_reply_markup(
            reply_markup=None
        )

    except Exception:

        pass

    await OrderForm.waiting_for_phone.set()

    await call.message.answer(
        f"🎨 Вы выбрали: <b>{safe(color_name)}</b>\n\n"
        "Теперь отправьте номер телефона.\n\n"
        "Можно нажать кнопку "
        "<b>«📱 Отправить телефон»</b> "
        "или написать номер вручную.",
        parse_mode="HTML",
        reply_markup=phone_keyboard()
    )


# ============================================================
# CANCEL CALLBACK
# ============================================================

@dp.callback_query_handler(
    lambda call: call.data == "cancel_order",
    state="*"
)
async def cancel_order_callback(
    call: types.CallbackQuery,
    state: FSMContext
):

    await state.finish()

    await call.answer(
        "Заказ отменён"
    )

    try:

        await call.message.edit_reply_markup(
            reply_markup=None
        )

    except Exception:

        pass

    await call.message.answer(
        "❌ Оформление заказа отменено.",
        reply_markup=main_keyboard()
    )


# ============================================================
# CANCEL BUTTON
# ============================================================

@dp.message_handler(
    lambda message: message.text == "❌ Отмена",
    state="*"
)
async def cancel_button(
    message: types.Message,
    state: FSMContext
):

    await state.finish()

    await message.answer(
        "❌ Оформление заказа отменено.",
        reply_markup=main_keyboard()
    )


# ============================================================
# PHONE — CONTACT
# ============================================================

@dp.message_handler(
    content_types=types.ContentType.CONTACT,
    state=OrderForm.waiting_for_phone
)
async def receive_contact(
    message: types.Message,
    state: FSMContext
):

    phone = message.contact.phone_number

    await state.update_data(
        phone=phone
    )

    await OrderForm.waiting_for_address.set()

    await message.answer(
        "📍 Отлично!\n\n"
        "Теперь отправьте "
        "<b>адрес доставки одним сообщением</b>.\n\n"
        "Например:\n"
        "<i>Санкт-Петербург, "
        "Невский проспект, 10, кв. 25</i>",
        parse_mode="HTML",
        reply_markup=cancel_keyboard()
    )


# ============================================================
# PHONE — TEXT
# ============================================================

@dp.message_handler(
    state=OrderForm.waiting_for_phone
)
async def receive_phone_text(
    message: types.Message,
    state: FSMContext
):

    phone = (message.text or "").strip()

    if len(phone) < 5:

        await message.answer(
            "⚠️ Пожалуйста, отправьте корректный "
            "номер телефона."
        )

        return

    await state.update_data(
        phone=phone
    )

    await OrderForm.waiting_for_address.set()

    await message.answer(
        "📍 Теперь отправьте "
        "<b>адрес доставки одним сообщением</b>.\n\n"
        "Например:\n"
        "<i>Санкт-Петербург, "
        "Невский проспект, 10, кв. 25</i>",
        parse_mode="HTML",
        reply_markup=cancel_keyboard()
    )


# ============================================================
# ADDRESS
# ============================================================

@dp.message_handler(
    state=OrderForm.waiting_for_address
)
async def receive_address(
    message: types.Message,
    state: FSMContext
):

    address = (message.text or "").strip()

    if len(address) < 5:

        await message.answer(
            "⚠️ Пожалуйста, укажите полный "
            "адрес доставки."
        )

        return

    data = await state.get_data()

    color_name = data.get(
        "color_name",
        "не указан"
    )

    phone = data.get(
        "phone",
        "не указан"
    )

    order_id = generate_order_id()

    client_id = message.from_user.id

    client_name = user_name(
        message.from_user
    )

    client_username = username(
        message.from_user
    )

    created_at = datetime.now()

    order = {
        "id": order_id,
        "client_id": client_id,
        "client_name": client_name,
        "username": client_username,
        "phone": phone,
        "address": address,
        "color": color_name,
        "product": PRODUCT_NAME,
        "price": PRICE,
        "status": "new",
        "created_at": created_at,
    }

    # --------------------------------------------------------
    # SAVE TO DATABASE FIRST
    # --------------------------------------------------------

    try:

        save_order(order)

    except Exception as error:

        logger.exception(
            "Failed to save order: %s",
            error
        )

        await message.answer(
            "⚠️ Произошла ошибка при сохранении заказа.\n\n"
            "Пожалуйста, попробуйте ещё раз.",
            reply_markup=main_keyboard()
        )

        return

    await state.finish()

    created_at_text = created_at.strftime(
        "%d.%m.%Y %H:%M"
    )

    # --------------------------------------------------------
    # ADMIN MESSAGE
    # --------------------------------------------------------

    admin_text = (
        "🆕 <b>НОВЫЙ ЗАКАЗ UTTA</b>\n\n"

        f"🔖 <b>Заказ:</b> #{safe(order_id)}\n\n"

        f"🐾 <b>Товар:</b> {safe(PRODUCT_NAME)}\n"
        f"🎨 <b>Цвет:</b> {safe(color_name)}\n"
        f"💰 <b>Цена:</b> {PRICE:,} ₽\n\n"

        f"👤 <b>Клиент:</b> {safe(client_name)}\n"
        f"💬 <b>Telegram:</b> "
        f"{safe(client_username)}\n"
        f"📱 <b>Телефон:</b> {safe(phone)}\n"
        f"📍 <b>Адрес:</b> {safe(address)}\n\n"

        f"📊 <b>Статус:</b> 🆕 Новый\n"
        f"🕐 <b>Создан:</b> {created_at_text}"
    ).replace(",", " ")

    try:

        await bot.send_message(
            ADMIN_ID,
            admin_text,
            parse_mode="HTML",
            reply_markup=admin_order_keyboard(
                order_id
            )
        )

    except Exception as error:

        logger.exception(
            "Failed to send order to admin: %s",
            error
        )

        await message.answer(
            "⚠️ Заказ сохранён, но не удалось "
            "отправить уведомление администратору.\n\n"
            "Мы сохранили заказ в системе.",
            reply_markup=main_keyboard()
        )

        return

    # --------------------------------------------------------
    # CLIENT CONFIRMATION
    # --------------------------------------------------------

    client_text = (
        "✅ <b>Заказ принят!</b>\n\n"

        "Спасибо за заказ в <b>UTTA</b> 🐾\n\n"

        f"🔖 Номер заказа: "
        f"<b>#{safe(order_id)}</b>\n"

        f"🐾 Товар: {safe(PRODUCT_NAME)}\n"

        f"🎨 Цвет: {safe(color_name)}\n"

        f"💰 Сумма: <b>{PRICE:,} ₽</b>\n\n"

        "Мы свяжемся с вами для подтверждения "
        "деталей и оплаты."
    ).replace(",", " ")

    await message.answer(
        client_text,
        parse_mode="HTML",
        reply_markup=main_keyboard()
    )


# ============================================================
# ADMIN — ACCEPT
# ============================================================

@dp.callback_query_handler(
    lambda call: call.data.startswith("accept:")
)
async def admin_accept_order(
    call: types.CallbackQuery
):

    if call.from_user.id != ADMIN_ID:

        await call.answer(
            "Нет доступа",
            show_alert=True
        )

        return

    order_id = call.data.split(":", 1)[1]

    order = get_order(order_id)

    if not order:

        await call.answer(
            "Заказ не найден",
            show_alert=True
        )

        return

    update_order_status(
        order_id,
        "accepted"
    )

    await call.answer(
        "Заказ принят"
    )

    try:

        await call.message.edit_reply_markup(
            reply_markup=None
        )

    except Exception:

        pass

    await call.message.answer(
        "✅ <b>Заказ принят</b>\n\n"
        f"🔖 Заказ: <b>#{safe(order_id)}</b>\n"
        f"👤 Клиент: {safe(order['client_name'])}\n"
        f"🎨 Цвет: {safe(order['color'])}\n"
        f"💰 Сумма: <b>{order['price']:,} ₽</b>\n\n"
        "📊 Статус: <b>Принят</b>",
        parse_mode="HTML"
    )

    try:

        await bot.send_message(
            order["client_id"],
            "🎉 <b>Ваш заказ принят!</b>\n\n"
            f"🔖 Номер заказа: "
            f"<b>#{safe(order_id)}</b>\n\n"
            "Мы свяжемся с вами для "
            "подтверждения оплаты и доставки.",
            parse_mode="HTML"
        )

    except Exception as error:

        logger.warning(
            "Could not notify client: %s",
            error
        )


# ============================================================
# ADMIN — REJECT
# ============================================================

@dp.callback_query_handler(
    lambda call: call.data.startswith("reject:")
)
async def admin_reject_order(
    call: types.CallbackQuery
):

    if call.from_user.id != ADMIN_ID:

        await call.answer(
            "Нет доступа",
            show_alert=True
        )

        return

    order_id = call.data.split(":", 1)[1]

    order = get_order(order_id)

    if not order:

        await call.answer(
            "Заказ не найден",
            show_alert=True
        )

        return

    update_order_status(
        order_id,
        "rejected"
    )

    await call.answer(
        "Заказ отклонён"
    )

    try:

        await call.message.edit_reply_markup(
            reply_markup=None
        )

    except Exception:

        pass

    await call.message.answer(
        "❌ <b>Заказ отклонён</b>\n\n"
        f"🔖 Заказ: <b>#{safe(order_id)}</b>\n"
        f"👤 Клиент: {safe(order['client_name'])}\n\n"
        "📊 Статус: <b>Отклонён</b>",
        parse_mode="HTML"
    )

    try:

        await bot.send_message(
            order["client_id"],
            "ℹ️ <b>По вашему заказу произошли изменения.</b>\n\n"
            f"🔖 Номер заказа: "
            f"<b>#{safe(order_id)}</b>\n\n"
            "Пожалуйста, свяжитесь с нами.",
            parse_mode="HTML"
        )

    except Exception as error:

        logger.warning(
            "Could not notify client: %s",
            error
        )


# ============================================================
# ADMIN — /orders
# ============================================================

@dp.message_handler(
    commands=["orders"],
    state="*"
)
async def admin_orders(
    message: types.Message,
    state: FSMContext
):

    await state.finish()

    if message.from_user.id != ADMIN_ID:

        await message.answer(
            "⛔ Нет доступа."
        )

        return

    try:

        orders = get_recent_orders(20)

    except Exception as error:

        logger.exception(
            "Failed to get orders: %s",
            error
        )

        await message.answer(
            "⚠️ Ошибка базы данных."
        )

        return

    if not orders:

        await message.answer(
            "📦 Заказов пока нет."
        )

        return

    text = "📦 <b>Последние заказы</b>\n\n"

    for order in orders:

        created = order["created_at"]

        if hasattr(created, "strftime"):
            created = created.strftime(
                "%d.%m.%Y %H:%M"
            )

        text += (
            f"🔖 <b>#{safe(order['id'])}</b>\n"
            f"🐾 {safe(order['product'])}\n"
            f"🎨 {safe(order['color'])}\n"
            f"💰 {order['price']:,} ₽\n"
            f"👤 {safe(order['client_name'])}\n"
            f"📊 {status_text(order['status'])}\n"
            f"🕐 {created}\n\n"
        )

    await message.answer(
        text.replace(",", " "),
        parse_mode="HTML"
    )


# ============================================================
# ADMIN — /order
# ============================================================

@dp.message_handler(
    commands=["order"],
    state="*"
)
async def admin_single_order(
    message: types.Message,
    state: FSMContext
):

    await state.finish()

    if message.from_user.id != ADMIN_ID:

        await message.answer(
            "⛔ Нет доступа."
        )

        return

    parts = message.text.split()

    if len(parts) != 2:

        await message.answer(
            "Использование:\n"
            "<code>/order 8AC32B41</code>",
            parse_mode="HTML"
        )

        return

    order_id = parts[1].replace("#", "").upper()

    order = get_order(order_id)

    if not order:

        await message.answer(
            "❌ Заказ не найден."
        )

        return

    created = order["created_at"]

    if hasattr(created, "strftime"):
        created = created.strftime(
            "%d.%m.%Y %H:%M"
        )

    text = (
        "📦 <b>Информация о заказе</b>\n\n"
        f"🔖 <b>#{safe(order['id'])}</b>\n"
        f"🐾 Товар: {safe(order['product'])}\n"
        f"🎨 Цвет: {safe(order['color'])}\n"
        f"💰 Цена: <b>{order['price']:,} ₽</b>\n\n"
        f"👤 Клиент: {safe(order['client_name'])}\n"
        f"💬 Telegram: {safe(order['username'])}\n"
        f"📱 Телефон: {safe(order['phone'])}\n"
        f"📍 Адрес: {safe(order['address'])}\n\n"
        f"📊 Статус: <b>{status_text(order['status'])}</b>\n"
        f"🕐 Создан: {created}"
    ).replace(",", " ")

    await message.answer(
        text,
        parse_mode="HTML"
    )


# ============================================================
# ERROR HANDLER
# ============================================================

@dp.errors_handler()
async def errors_handler(
    update,
    exception
):

    logger.exception(
        "Unhandled bot error: %s",
        exception
    )

    return True


# ============================================================
# STARTUP
# ============================================================

async def on_startup(
    dispatcher
):

    logger.info("Starting UTTA bot...")

    init_database()

    # Remove old webhook and pending updates.
    # We use polling on Render.
    try:

        await bot.delete_webhook(
            drop_pending_updates=True
        )

    except Exception as error:

        logger.warning(
            "Could not delete webhook: %s",
            error
        )

    logger.info(
        "UTTA bot started successfully"
    )


# ============================================================
# SHUTDOWN
# ============================================================

async def on_shutdown(
    dispatcher
):

    logger.info(
        "Stopping UTTA bot..."
    )

    await bot.session.close()


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    executor.start_polling(
        dp,
        skip_updates=True,
        on_startup=on_startup,
        on_shutdown=on_shutdown
    )
