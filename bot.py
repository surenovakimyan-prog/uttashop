import html
import logging
import os
import secrets
from datetime import datetime

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

if not TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

if not ADMIN_ID_RAW:
    raise RuntimeError("ADMIN_ID is not set")

try:
    ADMIN_ID = int(ADMIN_ID_RAW)
except ValueError:
    raise RuntimeError("ADMIN_ID must be a number")


# Render automatically provides this variable.
RENDER_URL = os.getenv(
    "RENDER_EXTERNAL_URL",
    "https://uttashop.onrender.com"
).rstrip("/")

PORT = int(os.getenv("PORT", "10000"))

WEBHOOK_PATH = "/telegram/webhook"
WEBHOOK_URL = f"{RENDER_URL}{WEBHOOK_PATH}"


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
# ORDERS
# ============================================================

orders = {}


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

def generate_order_id():

    order_id = secrets.token_hex(4).upper()

    while order_id in orders:
        order_id = secrets.token_hex(4).upper()

    return order_id


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


def safe(value):

    return html.escape(str(value))


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

    created_at = datetime.now().strftime(
        "%d.%m.%Y %H:%M"
    )

    orders[order_id] = {

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

    await state.finish()

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

        f"🕐 <b>Создан:</b> {created_at}"
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
            "⚠️ Не удалось отправить заказ "
            "администратору.\n\n"
            "Пожалуйста, попробуйте ещё раз "
            "или свяжитесь с нами напрямую.",
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

        "Мы свяжемся с вами для "
        "подтверждения заказа и оплаты."
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
async def accept_order(
    call: types.CallbackQuery
):

    if call.from_user.id != ADMIN_ID:

        await call.answer(
            "⛔ У вас нет доступа.",
            show_alert=True
        )

        return

    order_id = call.data.split(":", 1)[1]

    order = orders.get(order_id)

    if not order:

        await call.answer(
            "Заказ не найден.",
            show_alert=True
        )

        return

    if order["status"] != "new":

        await call.answer(
            "Этот заказ уже обработан.",
            show_alert=True
        )

        return

    order["status"] = "accepted"

    updated_text = (
        "🟢 <b>ЗАКАЗ ПРИНЯТ</b>\n\n"

        f"🔖 <b>Заказ:</b> #{safe(order['id'])}\n\n"

        f"🐾 <b>Товар:</b> "
        f"{safe(order['product'])}\n"

        f"🎨 <b>Цвет:</b> "
        f"{safe(order['color'])}\n"

        f"💰 <b>Цена:</b> "
        f"{order['price']:,} ₽\n\n"

        f"👤 <b>Клиент:</b> "
        f"{safe(order['client_name'])}\n"

        f"💬 <b>Telegram:</b> "
        f"{safe(order['username'])}\n"

        f"📱 <b>Телефон:</b> "
        f"{safe(order['phone'])}\n"

        f"📍 <b>Адрес:</b> "
        f"{safe(order['address'])}\n\n"

        "✅ <b>Статус:</b> заказ принят"
    ).replace(",", " ")

    try:

        await call.message.edit_text(
            updated_text,
            parse_mode="HTML"
        )

    except Exception:
        pass

    await call.answer(
        "Заказ принят ✅"
    )

    try:

        await bot.send_message(
            order["client_id"],
            (
                "🎉 <b>Ваш заказ принят!</b>\n\n"

                f"🔖 Заказ: "
                f"<b>#{safe(order['id'])}</b>\n"

                f"🐾 {safe(order['product'])}\n"

                f"🎨 {safe(order['color'])}\n"

                f"💰 {order['price']:,} ₽\n\n"

                "Мы свяжемся с вами для "
                "подтверждения деталей и оплаты. 🐾"
            ).replace(",", " "),
            parse_mode="HTML"
        )

    except Exception as error:

        logger.error(
            "Could not notify client: %s",
            error
        )


# ============================================================
# ADMIN — REJECT
# ============================================================

@dp.callback_query_handler(
    lambda call: call.data.startswith("reject:")
)
async def reject_order(
    call: types.CallbackQuery
):

    if call.from_user.id != ADMIN_ID:

        await call.answer(
            "⛔ У вас нет доступа.",
            show_alert=True
        )

        return

    order_id = call.data.split(":", 1)[1]

    order = orders.get(order_id)

    if not order:

        await call.answer(
            "Заказ не найден.",
            show_alert=True
        )

        return

    if order["status"] != "new":

        await call.answer(
            "Этот заказ уже обработан.",
            show_alert=True
        )

        return

    order["status"] = "rejected"

    rejected_text = (
        "🔴 <b>ЗАКАЗ ОТКЛОНЁН</b>\n\n"

        f"🔖 <b>Заказ:</b> #{safe(order['id'])}\n\n"

        f"🐾 <b>Товар:</b> "
        f"{safe(order['product'])}\n"

        f"🎨 <b>Цвет:</b> "
        f"{safe(order['color'])}\n"

        f"💰 <b>Цена:</b> "
        f"{order['price']:,} ₽\n\n"

        f"👤 <b>Клиент:</b> "
        f"{safe(order['client_name'])}\n"

        f"📱 <b>Телефон:</b> "
        f"{safe(order['phone'])}\n"

        f"📍 <b>Адрес:</b> "
        f"{safe(order['address'])}\n\n"

        "❌ <b>Статус:</b> заказ отклонён"
    ).replace(",", " ")

    try:

        await call.message.edit_text(
            rejected_text,
            parse_mode="HTML"
        )

    except Exception:
        pass

    await call.answer(
        "Заказ отклонён"
    )

    try:

        await bot.send_message(
            order["client_id"],
            (
                "ℹ️ <b>По вашему заказу</b>\n\n"
                f"Заказ <b>#{safe(order['id'])}</b> "
                "не удалось принять в работу.\n\n"
                "Пожалуйста, свяжитесь с нами "
                "для уточнения деталей."
            ),
            parse_mode="HTML"
        )

    except Exception as error:

        logger.error(
            "Could not notify rejected client: %s",
            error
        )


# ============================================================
# ABOUT SHOP
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

        "UTTA — бренд стильных "
        "аксессуаров для собак. 🐾\n\n"

        "Мы создаём аксессуары, которые "
        "сочетают эстетику, комфорт и качество.\n\n"

        "🦮 Сейчас в продаже:\n"
        "Премиальные поводки UTTA\n\n"

        "🎨 Розовый\n"
        "🎨 Голубой\n"
        "🎨 Салатовый\n\n"

        "💰 Цена: <b>2 000 ₽</b>"
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

        "🐾 Мы обязательно ответим."
    )

    keyboard = InlineKeyboardMarkup()

    keyboard.add(
        InlineKeyboardButton(
            "💬 Написать администратору",
            url="https://t.me/dr_ovakimyan"
        )
    )

    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=keyboard
    )


# ============================================================
# UNKNOWN MESSAGE
# ============================================================

@dp.message_handler(
    state="*"
)
async def unknown_message(
    message: types.Message,
    state: FSMContext
):

    current_state = await state.get_state()

    if current_state:
        return

    await message.answer(
        "🐾 Выберите действие в меню ниже.",
        reply_markup=main_keyboard()
    )


# ============================================================
# WEBHOOK STARTUP
# ============================================================

async def on_startup(dispatcher):

    logger.info("====================================")
    logger.info("UTTA BOT STARTING")
    logger.info("Webhook URL: %s", WEBHOOK_URL)
    logger.info("Admin ID: %s", ADMIN_ID)
    logger.info("Port: %s", PORT)
    logger.info("====================================")

    # Устанавливаем webhook.
    await bot.set_webhook(
        WEBHOOK_URL,
        drop_pending_updates=True
    )

    logger.info(
        "Webhook successfully configured"
    )


# ============================================================
# SHUTDOWN
# ============================================================

async def on_shutdown(dispatcher):

    logger.info("UTTA BOT STOPPING")

    try:

        await bot.delete_webhook()

    except Exception as error:

        logger.warning(
            "Could not delete webhook: %s",
            error
        )

    await storage.close()
    await storage.wait_closed()

    await bot.session.close()


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    logger.info(
        "Starting UTTA webhook server..."
    )

    executor.start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        skip_updates=True,
        host="0.0.0.0",
        port=PORT
    )
