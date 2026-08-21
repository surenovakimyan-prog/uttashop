import asyncio
import os
from datetime import datetime

from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.filters import CommandStart


# ============================================================
# CONFIG
# ============================================================

from config import TOKEN, ADMIN_ID


# ============================================================
# BOT
# ============================================================

bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())


# ============================================================
# PRODUCTS
# ============================================================

PRODUCTS = {
    "leash": {
        "name": "Премиальный поводок UTTA",
        "price": 2000,
        "description": (
            "Стильный поводок ручной работы для собак.\n\n"
            "✨ Премиальный внешний вид\n"
            "🐾 Подходит для маленьких и средних пород\n"
            "💎 Надёжная фурнитура\n"
            "🎨 Несколько цветов"
        ),
        "colors": {
            "pink": "💗 Розовый",
            "blue": "💙 Синий",
            "green": "💚 Салатовый",
        },
    }
}


# ============================================================
# ORDER STORAGE
# ============================================================

orders = {}

order_counter = 1


def get_next_order_number():
    global order_counter

    number = f"UTTA-{order_counter:04d}"
    order_counter += 1

    return number


# ============================================================
# FSM
# ============================================================

class OrderState(StatesGroup):
    waiting_phone = State()
    waiting_address = State()


# ============================================================
# KEYBOARDS
# ============================================================

def main_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)

    kb.row(
        KeyboardButton("🛍 Каталог")
    )

    kb.row(
        KeyboardButton("ℹ️ О магазине"),
        KeyboardButton("📩 Связаться")
    )

    return kb


def catalog_keyboard():
    kb = InlineKeyboardMarkup(row_width=1)

    kb.add(
        InlineKeyboardButton(
            "🦮 Премиальный поводок UTTA — 2 000 ₽",
            callback_data="product:leash"
        )
    )

    return kb


def color_keyboard():
    kb = InlineKeyboardMarkup(row_width=1)

    kb.add(
        InlineKeyboardButton(
            "💗 Розовый",
            callback_data="color:pink"
        )
    )

    kb.add(
        InlineKeyboardButton(
            "💙 Синий",
            callback_data="color:blue"
        )
    )

    kb.add(
        InlineKeyboardButton(
            "💚 Салатовый",
            callback_data="color:green"
        )
    )

    kb.add(
        InlineKeyboardButton(
            "⬅️ Назад в каталог",
            callback_data="back:catalog"
        )
    )

    return kb


def after_product_keyboard():
    kb = InlineKeyboardMarkup(row_width=1)

    kb.add(
        InlineKeyboardButton(
            "🛒 Перейти в корзину",
            callback_data="cart"
        )
    )

    kb.add(
        InlineKeyboardButton(
            "🛍 Продолжить покупки",
            callback_data="back:catalog"
        )
    )

    return kb


def cart_keyboard():
    kb = InlineKeyboardMarkup(row_width=1)

    kb.add(
        InlineKeyboardButton(
            "📦 Оформить заказ",
            callback_data="checkout"
        )
    )

    kb.add(
        InlineKeyboardButton(
            "🛍 Вернуться в каталог",
            callback_data="back:catalog"
        )
    )

    return kb


# ============================================================
# START
# ============================================================

@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    text = (
        "🐾 <b>Добро пожаловать в UTTA!</b>\n\n"
        "Стильные аксессуары для собак.\n\n"
        "Выберите нужный раздел ниже 👇"
    )

    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=main_menu()
    )


# ============================================================
# CATALOG
# ============================================================

@dp.message_handler(lambda message: message.text == "🛍 Каталог")
async def catalog(message: types.Message):

    product = PRODUCTS["leash"]

    text = (
        "🛍 <b>КАТАЛОГ UTTA</b>\n\n"
        f"🦮 <b>{product['name']}</b>\n\n"
        f"{product['description']}\n\n"
        f"💰 Цена: <b>{product['price']:,} ₽</b>\n\n"
        "Нажмите на товар, чтобы посмотреть варианты."
    ).replace(",", " ")

    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=catalog_keyboard()
    )


# ============================================================
# PRODUCT
# ============================================================

@dp.callback_query_handler(lambda c: c.data == "product:leash")
async def product(callback: types.CallbackQuery):

    product = PRODUCTS["leash"]

    text = (
        f"🦮 <b>{product['name']}</b>\n\n"
        f"{product['description']}\n\n"
        f"💰 Цена: <b>{product['price']:,} ₽</b>\n\n"
        "🎨 Выберите цвет:"
    ).replace(",", " ")

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=color_keyboard()
    )

    await callback.answer()


# ============================================================
# COLOR
# ============================================================

@dp.callback_query_handler(lambda c: c.data.startswith("color:"))
async def choose_color(callback: types.CallbackQuery):

    color_code = callback.data.split(":")[1]

    product = PRODUCTS["leash"]
    color_name = product["colors"][color_code]

    user_id = callback.from_user.id

    # Создаём корзину пользователя
    if user_id not in orders:
        orders[user_id] = {
            "items": [],
            "phone": None,
            "address": None,
        }

    orders[user_id]["items"].append({
        "product": product["name"],
        "color": color_name,
        "price": product["price"],
        "quantity": 1,
    })

    text = (
        "✅ <b>Товар добавлен в корзину!</b>\n\n"
        f"🦮 {product['name']}\n"
        f"🎨 Цвет: {color_name}\n"
        f"💰 Цена: {product['price']:,} ₽\n\n"
        "Что хотите сделать дальше?"
    ).replace(",", " ")

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=after_product_keyboard()
    )

    await callback.answer("Добавлено в корзину 🛒")


# ============================================================
# CART
# ============================================================

@dp.callback_query_handler(lambda c: c.data == "cart")
async def show_cart(callback: types.CallbackQuery):

    user_id = callback.from_user.id

    if user_id not in orders or not orders[user_id]["items"]:
        await callback.answer("Корзина пустая", show_alert=True)
        return

    items = orders[user_id]["items"]

    total = sum(
        item["price"] * item["quantity"]
        for item in items
    )

    text = "🛒 <b>ВАША КОРЗИНА</b>\n\n"

    for index, item in enumerate(items, start=1):

        text += (
            f"{index}. 🦮 {item['product']}\n"
            f"   🎨 {item['color']}\n"
            f"   🔢 Количество: {item['quantity']}\n"
            f"   💰 {item['price']:,} ₽\n\n"
        ).replace(",", " ")

    text += (
        "━━━━━━━━━━━━━━\n"
        f"💰 <b>ИТОГО: {total:,} ₽</b>"
    ).replace(",", " ")

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=cart_keyboard()
    )

    await callback.answer()


# ============================================================
# CHECKOUT
# ============================================================

@dp.callback_query_handler(lambda c: c.data == "checkout")
async def checkout(callback: types.CallbackQuery):

    user_id = callback.from_user.id

    if user_id not in orders or not orders[user_id]["items"]:
        await callback.answer(
            "Корзина пустая",
            show_alert=True
        )
        return

    kb = ReplyKeyboardMarkup(
        resize_keyboard=True,
        one_time_keyboard=True
    )

    kb.add(
        KeyboardButton(
            "📱 Отправить номер телефона",
            request_contact=True
        )
    )

    await callback.message.answer(
        "📱 <b>Оформление заказа</b>\n\n"
        "Пожалуйста, отправьте ваш номер телефона.\n\n"
        "Нажмите кнопку ниже 👇",
        parse_mode="HTML",
        reply_markup=kb
    )

    await OrderState.waiting_phone.set()

    await callback.answer()


# ============================================================
# PHONE
# ============================================================

@dp.message_handler(
    content_types=types.ContentType.CONTACT,
    state=OrderState.waiting_phone
)
async def receive_phone(
    message: types.Message,
    state: FSMContext
):

    user_id = message.from_user.id

    phone = message.contact.phone_number

    if user_id not in orders:
        orders[user_id] = {
            "items": [],
            "phone": None,
            "address": None,
        }

    orders[user_id]["phone"] = phone

    await message.answer(
        "Спасибо! 👍\n\n"
        "📍 Теперь напишите <b>адрес доставки</b> "
        "одним сообщением.\n\n"
        "Например:\n"
        "Москва, ул. Ленина, д. 10, кв. 25",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove()
    )

    await OrderState.waiting_address.set()


# ============================================================
# ADDRESS
# ============================================================

@dp.message_handler(
    state=OrderState.waiting_address,
    content_types=types.ContentType.TEXT
)
async def receive_address(
    message: types.Message,
    state: FSMContext
):

    user_id = message.from_user.id

    address = message.text.strip()

    orders[user_id]["address"] = address

    order_number = get_next_order_number()

    items = orders[user_id]["items"]

    total = sum(
        item["price"] * item["quantity"]
        for item in items
    )

    username = (
        f"@{message.from_user.username}"
        if message.from_user.username
        else "не указан"
    )

    full_name = message.from_user.full_name

    # --------------------------------------------------------
    # ADMIN MESSAGE
    # --------------------------------------------------------

    admin_text = (
        "🆕 <b>НОВЫЙ ЗАКАЗ UTTA</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 <b>Заказ:</b> {order_number}\n\n"
    )

    for index, item in enumerate(items, start=1):

        admin_text += (
            f"<b>Товар {index}</b>\n"
            f"🦮 {item['product']}\n"
            f"🎨 Цвет: {item['color']}\n"
            f"🔢 Количество: {item['quantity']}\n"
            f"💰 Цена: {item['price']:,} ₽\n\n"
        ).replace(",", " ")

    admin_text += (
        "━━━━━━━━━━━━━━━━━━\n"
        f"💰 <b>ИТОГО: {total:,} ₽</b>\n\n"
        "👤 <b>Клиент</b>\n"
        f"Имя: {full_name}\n"
        f"Telegram: {username}\n"
        f"ID: <code>{user_id}</code>\n"
        f"📱 Телефон: {orders[user_id]['phone']}\n"
        f"📍 Адрес: {address}\n"
    ).replace(",", " ")

    # --------------------------------------------------------
    # SEND TO ADMIN
    # --------------------------------------------------------

    try:
        await bot.send_message(
            ADMIN_ID,
            admin_text,
            parse_mode="HTML"
        )
    except Exception as e:
        print("ADMIN SEND ERROR:", e)

    # --------------------------------------------------------
    # CUSTOMER CONFIRMATION
    # --------------------------------------------------------

    customer_text = (
        "✅ <b>Заказ принят!</b>\n\n"
        f"📦 Номер заказа: <b>{order_number}</b>\n\n"
        f"💰 Сумма: <b>{total:,} ₽</b>\n\n"
        "Мы свяжемся с вами для подтверждения "
        "заказа и оплаты.\n\n"
        "Спасибо, что выбираете <b>UTTA</b> 🐾"
    ).replace(",", " ")

    await message.answer(
        customer_text,
        parse_mode="HTML",
        reply_markup=main_menu()
    )

    # --------------------------------------------------------
    # CLEAR USER CART
    # --------------------------------------------------------

    orders[user_id] = {
        "items": [],
        "phone": None,
        "address": None,
    }

    await state.finish()


# ============================================================
# ABOUT
# ============================================================

@dp.message_handler(lambda message: message.text == "ℹ️ О магазине")
async def about(message: types.Message):

    text = (
        "🐾 <b>UTTA</b>\n\n"
        "Стильные аксессуары для собак.\n\n"
        "Мы создаём красивые и удобные аксессуары "
        "для прогулок с вашим питомцем.\n\n"
        "✨ Премиальный дизайн\n"
        "🐶 Для маленьких и средних пород\n"
        "💎 Качественная фурнитура\n"
        "❤️ Сделано с любовью к собакам\n\n"
        "Добро пожаловать в UTTA!"
    )

    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=main_menu()
    )


# ============================================================
# CONTACT
# ============================================================

@dp.message_handler(lambda message: message.text == "📩 Связаться")
async def contact(message: types.Message):

    await message.answer(
        "📩 <b>Связаться с UTTA</b>\n\n"
        "Если у вас есть вопрос по товару или заказу — "
        "напишите нам.\n\n"
        "Мы обязательно ответим 🐾",
        parse_mode="HTML",
        reply_markup=main_menu()
    )


# ============================================================
# BACK TO CATALOG
# ============================================================

@dp.callback_query_handler(lambda c: c.data == "back:catalog")
async def back_catalog(callback: types.CallbackQuery):

    product = PRODUCTS["leash"]

    text = (
        "🛍 <b>КАТАЛОГ UTTA</b>\n\n"
        f"🦮 <b>{product['name']}</b>\n\n"
        f"{product['description']}\n\n"
        f"💰 Цена: <b>{product['price']:,} ₽</b>"
    ).replace(",", " ")

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=catalog_keyboard()
    )

    await callback.answer()


# ============================================================
# ERROR HANDLER
# ============================================================

@dp.errors_handler()
async def errors_handler(update, exception):

    print("BOT ERROR:", exception)

    return True


# ============================================================
# START BOT
# ============================================================

if __name__ == "__main__":

    print("===================================")
    print("UTTA BOT STARTED")
    print("===================================")

    executor.start_polling(
        dp,
        skip_updates=True
    )
