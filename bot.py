import asyncio
import logging
import os
from aiohttp import web

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

# ============================================================
# CONFIG
# ============================================================

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

if not ADMIN_ID:
    raise RuntimeError("ADMIN_ID is not set")

ADMIN_ID = int(ADMIN_ID)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

bot = Bot(token=TOKEN, parse_mode="HTML")
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


# ============================================================
# PRODUCT
# ============================================================

PRODUCT_NAME = "Премиальный поводок UTTA"
PRODUCT_PRICE = 2000

COLORS = {
    "pink": "💗 Розовый",
    "blue": "💙 Голубой",
    "green": "💚 Салатовый",
}


# ============================================================
# STATES
# ============================================================

class OrderForm(StatesGroup):
    waiting_color = State()
    waiting_phone = State()
    waiting_address = State()


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


def catalog_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)

    keyboard.add(
        InlineKeyboardButton(
            "🐾 Премиальный поводок UTTA — 2 000 ₽",
            callback_data="product_leash"
        )
    )

    return keyboard


def color_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)

    keyboard.add(
        InlineKeyboardButton(
            "💗 Розовый",
            callback_data="color_pink"
        )
    )

    keyboard.add(
        InlineKeyboardButton(
            "💙 Голубой",
            callback_data="color_blue"
        )
    )

    keyboard.add(
        InlineKeyboardButton(
            "💚 Салатовый",
            callback_data="color_green"
        )
    )

    keyboard.add(
        InlineKeyboardButton(
            "❌ Отмена",
            callback_data="cancel_order"
        )
    )

    return keyboard


def phone_keyboard():
    keyboard = ReplyKeyboardMarkup(
        resize_keyboard=True,
        one_time_keyboard=True
    )

    keyboard.add(
        KeyboardButton(
            "📱 Отправить номер телефона",
            request_contact=True
        )
    )

    keyboard.add(
        KeyboardButton("❌ Отмена")
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


# ============================================================
# START
# ============================================================

@dp.message_handler(commands=["start"], state="*")
async def start_command(message: types.Message, state: FSMContext):
    await state.finish()

    text = (
        "🐾 <b>Добро пожаловать в UTTA!</b>\n\n"
        "Премиальные аксессуары для собак.\n\n"
        "✨ Стиль\n"
        "✨ Качество\n"
        "✨ Комфорт для вашего питомца\n\n"
        "Выберите нужный раздел:"
    )

    await message.answer(
        text,
        reply_markup=main_keyboard()
    )


# ============================================================
# CATALOG
# ============================================================

@dp.message_handler(
    lambda message: message.text == "🛍 Каталог",
    state="*"
)
async def catalog(message: types.Message):
    await OrderForm.waiting_color.set()

    text = (
        "🛍 <b>Каталог UTTA</b>\n\n"
        f"🐾 <b>{PRODUCT_NAME}</b>\n\n"
        "Премиальный поводок для собак.\n\n"
        "🎨 Доступные цвета:\n"
        "💗 Розовый\n"
        "💙 Голубой\n"
        "💚 Салатовый\n\n"
        f"💰 Цена: <b>{PRODUCT_PRICE:,} ₽</b>\n\n"
        "Выберите цвет:"
    ).replace(",", " ")

    await message.answer(
        text,
        reply_markup=color_keyboard()
    )


# ============================================================
# PRODUCT CALLBACK
# ============================================================

@dp.callback_query_handler(
    lambda call: call.data == "product_leash",
    state="*"
)
async def product_callback(call: types.CallbackQuery):
    await call.answer()

    await call.message.answer(
        f"🐾 <b>{PRODUCT_NAME}</b>\n\n"
        f"💰 Цена: <b>{PRODUCT_PRICE:,} ₽</b>\n\n"
        "Выберите цвет:",
        reply_markup=color_keyboard()
    )


# ============================================================
# COLOR
# ============================================================

@dp.callback_query_handler(
    lambda call: call.data.startswith("color_"),
    state=OrderForm.waiting_color
)
async def choose_color(
    call: types.CallbackQuery,
    state: FSMContext
):
    await call.answer()

    color_key = call.data.replace("color_", "")

    if color_key not in COLORS:
        await call.message.answer(
            "❌ Неизвестный цвет."
        )
        return

    color = COLORS[color_key]

    await state.update_data(
        product=PRODUCT_NAME,
        price=PRODUCT_PRICE,
        color=color
    )

    await OrderForm.waiting_phone.set()

    await call.message.answer(
        f"Вы выбрали: <b>{color}</b>\n\n"
        "📱 Теперь отправьте номер телефона.\n\n"
        "Нажмите кнопку ниже — Telegram передаст номер автоматически.",
        reply_markup=phone_keyboard()
    )


# ============================================================
# PHONE
# ============================================================

@dp.message_handler(
    content_types=types.ContentType.CONTACT,
    state=OrderForm.waiting_phone
)
async def receive_phone(
    message: types.Message,
    state: FSMContext
):
    phone = message.contact.phone_number

    await state.update_data(
        phone=phone
    )

    await OrderForm.waiting_address.set()

    await message.answer(
        "📍 Отлично!\n\n"
        "Теперь отправьте <b>адрес доставки одним сообщением</b>.\n\n"
        "Например:\n"
        "<i>Санкт-Петербург, Невский проспект, 10, кв. 25</i>",
        reply_markup=cancel_keyboard()
    )


# ============================================================
# PHONE TEXT FALLBACK
# ============================================================

@dp.message_handler(
    state=OrderForm.waiting_phone
)
async def phone_fallback(
    message: types.Message
):
    await message.answer(
        "📱 Пожалуйста, нажмите кнопку "
        "<b>«📱 Отправить номер телефона»</b>, "
        "чтобы передать номер."
    )


# ============================================================
# ADDRESS
# ============================================================

@dp.message_handler(
    state=OrderForm.waiting_address
)
async def receive_address(
    message: types.Message,
    state: FSMContext
):
    address = message.text.strip()

    if len(address) < 5:
        await message.answer(
            "📍 Пожалуйста, укажите полный адрес доставки."
        )
        return

    data = await state.get_data()

    username = (
        f"@{message.from_user.username}"
        if message.from_user.username
        else "не указан"
    )

    full_name = (
        message.from_user.full_name
        if message.from_user.full_name
        else "не указано"
    )

    order_text = (
        "🆕 <b>НОВЫЙ ЗАКАЗ UTTA</b>\n\n"
        f"🐾 <b>Товар:</b> {data.get('product')}\n"
        f"🎨 <b>Цвет:</b> {data.get('color')}\n"
        f"💰 <b>Цена:</b> {data.get('price'):,} ₽\n\n"
        f"👤 <b>Клиент:</b> {full_name}\n"
        f"💬 <b>Telegram:</b> {username}\n"
        f"📱 <b>Телефон:</b> {data.get('phone')}\n"
        f"📍 <b>Адрес:</b> {address}\n"
    ).replace(",", " ")

    # Отправляем заказ администратору
    await bot.send_message(
        ADMIN_ID,
        order_text
    )

    # Подтверждение клиенту
    await message.answer(
        "✅ <b>Заказ принят!</b>\n\n"
        "Спасибо за заказ в UTTA 🐾\n\n"
        "Мы свяжемся с вами для подтверждения "
        "заказа и оплаты.",
        reply_markup=main_keyboard()
    )

    await state.finish()


# ============================================================
# ABOUT
# ============================================================

@dp.message_handler(
    lambda message: message.text == "ℹ️ О магазине",
    state="*"
)
async def about(message: types.Message):
    await message.answer(
        "🐾 <b>UTTA</b>\n\n"
        "Премиальные аксессуары для собак.\n\n"
        "Мы создаём стильные и удобные аксессуары "
        "для прогулок с вашими питомцами.\n\n"
        "✨ Качество\n"
        "✨ Стиль\n"
        "✨ Забота о питомцах\n\n"
        "Спасибо, что выбираете UTTA ❤️",
        reply_markup=main_keyboard()
    )


# ============================================================
# CONTACT
# ============================================================

@dp.message_handler(
    lambda message: message.text == "📩 Связаться",
    state="*"
)
async def contact(message: types.Message):
    await message.answer(
        "📩 <b>Связаться с UTTA</b>\n\n"
        "По вопросам заказа, оплаты и доставки "
        "напишите администратору магазина.\n\n"
        "Мы обязательно ответим ❤️",
        reply_markup=main_keyboard()
    )


# ============================================================
# CANCEL
# ============================================================

@dp.message_handler(
    lambda message: message.text == "❌ Отмена",
    state="*"
)
async def cancel_order(
    message: types.Message,
    state: FSMContext
):
    await state.finish()

    await message.answer(
        "❌ Заказ отменён.",
        reply_markup=main_keyboard()
    )


@dp.callback_query_handler(
    lambda call: call.data == "cancel_order",
    state="*"
)
async def cancel_callback(
    call: types.CallbackQuery,
    state: FSMContext
):
    await call.answer()

    await state.finish()

    await call.message.answer(
        "❌ Заказ отменён.",
        reply_markup=main_keyboard()
    )


# ============================================================
# UNKNOWN COMMAND / MESSAGE
# ============================================================

@dp.message_handler(state="*")
async def unknown_message(message: types.Message):
    await message.answer(
        "Я не совсем понял сообщение 😊\n\n"
        "Используйте кнопки меню ниже.",
        reply_markup=main_keyboard()
    )


# ============================================================
# RENDER HEALTH SERVER
# ============================================================

async def health_check(request):
    return web.Response(
        text="UttaPaws bot is running"
    )


async def start_web_server():
    port = int(os.getenv("PORT", "10000"))

    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        port
    )

    await site.start()

    logging.info(
        f"Health server started on port {port}"
    )


# ============================================================
# STARTUP
# ============================================================

async def on_startup(dispatcher):
    logging.info("====================================")
    logging.info("UTTAPAWS BOT STARTING")
    logging.info("====================================")

    await start_web_server()

    try:
        await bot.send_message(
            ADMIN_ID,
            "🟢 <b>UttaPaws запущен!</b>\n\n"
            "Бот готов принимать заказы."
        )
    except Exception as e:
        logging.warning(
            f"Could not send startup message: {e}"
        )


# ============================================================
# SHUTDOWN
# ============================================================

async def on_shutdown(dispatcher):
    logging.info("UttaPaws bot stopped.")

    await bot.close()
    await storage.close()


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    executor.start_polling(
        dp,
        skip_updates=True,
        on_startup=on_startup,
        on_shutdown=on_shutdown
    )
