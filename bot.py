import asyncio
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
# НАСТРОЙКИ
# ============================================================

# Бот берет данные из config.py
# В config.py должны быть:
#
# TOKEN = "ТОКЕН_БОТА"
# ADMIN_ID = 123456789

try:
    from config import TOKEN, ADMIN_ID
except ImportError:
    TOKEN = os.getenv("BOT_TOKEN")
    ADMIN_ID = os.getenv("ADMIN_ID")


if not TOKEN:
    raise RuntimeError("Не найден TOKEN. Проверь config.py или переменную BOT_TOKEN.")

if not ADMIN_ID:
    raise RuntimeError("Не найден ADMIN_ID. Проверь config.py или переменную ADMIN_ID.")

ADMIN_ID = int(ADMIN_ID)


# ============================================================
# ЛОГИРОВАНИЕ
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


# ============================================================
# BOT / DISPATCHER
# ============================================================

bot = Bot(token=TOKEN)
storage = MemoryStorage()

dp = Dispatcher(
    bot,
    storage=storage
)


# ============================================================
# ДАННЫЕ МАГАЗИНА
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
# FSM
# ============================================================

class OrderForm(StatesGroup):
    waiting_for_phone = State()
    waiting_for_address = State()


# ============================================================
# ВРЕМЕННЫЕ ЗАКАЗЫ
# ============================================================

# Храним заказы в памяти.
# Для текущей версии магазина этого достаточно.
orders = {}


# ============================================================
# КЛАВИАТУРЫ
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
            "✅ Принять заказ",
            callback_data=f"accept:{order_id}"
        ),
        InlineKeyboardButton(
            "❌ Отклонить",
            callback_data=f"reject:{order_id}"
        )
    )

    return keyboard


# ============================================================
# УТИЛИТЫ
# ============================================================

def generate_order_id():
    """
    Генерирует короткий уникальный номер заказа.
    Например: #A81F3C2D
    """

    return secrets.token_hex(4).upper()


def get_user_name(user: types.User):
    """
    Получаем имя клиента.
    """

    if user.full_name:
        return user.full_name

    if user.username:
        return f"@{user.username}"

    return "Клиент"


def format_username(user: types.User):
    """
    Возвращает Telegram пользователя.
    """

    if user.username:
        return f"@{user.username}"

    return "не указан"


# ============================================================
# START
# ============================================================

@dp.message_handler(commands=["start"], state="*")
async def cmd_start(message: types.Message, state: FSMContext):
    await state.finish()

    text = (
        "🐾 <b>Добро пожаловать в UTTA!</b>\n\n"
        "Премиальные аксессуары для собак.\n\n"
        "🦮 Сейчас в магазине доступен:\n"
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
# КАТАЛОГ
# ============================================================

@dp.message_handler(
    lambda message: message.text == "🛍 Каталог",
    state="*"
)
async def catalog(message: types.Message, state: FSMContext):
    await state.finish()

    text = (
        "🛍 <b>Каталог UTTA</b>\n\n"
        f"🐾 <b>{PRODUCT_NAME}</b>\n\n"
        "Стильный премиальный поводок для маленьких и средних собак.\n\n"
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
# ВЫБОР ЦВЕТА
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

    # Убираем inline-кнопки
    try:
        await call.message.edit_reply_markup(
            reply_markup=None
        )
    except Exception:
        pass

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

    await OrderForm.waiting_for_phone.set()

    await call.message.answer(
        f"🎨 Вы выбрали: <b>{color_name}</b>\n\n"
        "Теперь отправьте номер телефона.\n\n"
        "Можно нажать кнопку <b>«📱 Отправить телефон»</b> "
        "или написать номер вручную.",
        parse_mode="HTML",
        reply_markup=keyboard
    )


# ============================================================
# ТЕЛЕФОН
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

    keyboard = ReplyKeyboardMarkup(
        resize_keyboard=True
    )

    keyboard.add(
        KeyboardButton("❌ Отмена")
    )

    await message.answer(
        "📍 Отлично!\n\n"
        "Теперь отправьте <b>адрес доставки одним сообщением</b>.\n\n"
        "Например:\n"
        "<i>Санкт-Петербург, Невский проспект, 10, кв. 25</i>",
        parse_mode="HTML",
        reply_markup=keyboard
    )


@dp.message_handler(
    state=OrderForm.waiting_for_phone
)
async def receive_phone_text(
    message: types.Message,
    state: FSMContext
):

    phone = message.text.strip()

    if len(phone) < 5:
        await message.answer(
            "⚠️ Пожалуйста, отправьте корректный номер телефона."
        )
        return

    await state.update_data(
        phone=phone
    )

    await OrderForm.waiting_for_address.set()

    keyboard = ReplyKeyboardMarkup(
        resize_keyboard=True
    )

    keyboard.add(
        KeyboardButton("❌ Отмена")
    )

    await message.answer(
        "📍 Теперь отправьте <b>адрес доставки одним сообщением</b>.\n\n"
        "Например:\n"
        "<i>Санкт-Петербург, Невский проспект, 10, кв. 25</i>",
        parse_mode="HTML",
        reply_markup=keyboard
    )


# ============================================================
# АДРЕС → СОЗДАНИЕ ЗАКАЗА
# ============================================================

@dp.message_handler(
    state=OrderForm.waiting_for_address
)
async def receive_address(
    message: types.Message,
    state: FSMContext
):

    address = message.text.strip()

    if len(address) < 5:
        await message.answer(
            "⚠️ Пожалуйста, укажите полный адрес доставки."
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

    # На случай крайне маловероятного совпадения
    while order_id in orders:
        order_id = generate_order_id()

    client_id = message.from_user.id

    client_name = get_user_name(
        message.from_user
    )

    username = format_username(
        message.from_user
    )

    created_at = datetime.now().strftime(
        "%d.%m.%Y %H:%M"
    )

    orders[order_id] = {
        "id": order_id,
        "client_id": client_id,
        "client_name": client_name,
        "username": username,
        "phone": phone,
        "address": address,
        "color": color_name,
        "product": PRODUCT_NAME,
        "price": PRICE,
        "status": "new",
        "created_at": created_at,
    }

    # Завершаем FSM
    await state.finish()

    # Возвращаем обычное меню
    await message.answer(
        "⏳ Заказ оформляется...",
        reply_markup=main_keyboard()
    )

    # ========================================================
    # СООБЩЕНИЕ АДМИНИСТРАТОРУ
    # ========================================================

    admin_text = (
        "🆕 <b>НОВЫЙ ЗАКАЗ UTTA</b>\n\n"

        f"🔖 <b>Заказ:</b> #{order_id}\n\n"

        f"🐾 <b>Товар:</b> {PRODUCT_NAME}\n"
        f"🎨 <b>Цвет:</b> {color_name}\n"
        f"💰 <b>Цена:</b> {PRICE:,} ₽\n\n"

        f"👤 <b>Клиент:</b> {client_name}\n"
        f"💬 <b>Telegram:</b> {username}\n"
        f"📱 <b>Телефон:</b> {phone}\n"
        f"📍 <b>Адрес:</b> {address}\n\n"

        f"🕐 <b>Создан:</b> {created_at}"
    ).replace(",", " ")

    try:
        await bot.send_message(
            ADMIN_ID,
            admin_text,
            parse_mode="HTML",
            reply_markup=admin_order_keyboard(order_id)
        )

        logger.info(
            "Order %s sent to admin",
            order_id
        )

    except Exception as error:
        logger.exception(
            "Failed to send order to admin: %s",
            error
        )

        # Сообщаем клиенту, что произошла ошибка
        await message.answer(
            "⚠️ Произошла ошибка при отправке заказа.\n\n"
            "Пожалуйста, попробуйте оформить заказ ещё раз "
            "или свяжитесь с нами напрямую."
        )

        return

    # ========================================================
    # ПОДТВЕРЖДЕНИЕ КЛИЕНТУ
    # ========================================================

    client_text = (
        "✅ <b>Заказ принят!</b>\n\n"
        "Спасибо за заказ в <b>UTTA</b> 🐾\n\n"

        f"🔖 Номер заказа: <b>#{order_id}</b>\n"
        f"🐾 Товар: {PRODUCT_NAME}\n"
        f"🎨 Цвет: {color_name}\n"
        f"💰 Сумма: <b>{PRICE:,} ₽</b>\n\n"

        "Мы свяжемся с вами для подтверждения "
        "заказа и оплаты."
    ).replace(",", " ")

    await message.answer(
        client_text,
        parse_mode="HTML"
    )


# ============================================================
# АДМИН: ПРИНЯТЬ ЗАКАЗ
# ============================================================

@dp.callback_query_handler(
    lambda call: call.data.startswith("accept:")
)
async def accept_order(
    call: types.CallbackQuery
):

    # Проверяем, что кнопку нажимает администратор
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

    # Обновляем сообщение администратора
    updated_text = (
        "🟢 <b>ЗАКАЗ ПРИНЯТ</b>\n\n"

        f"🔖 <b>Заказ:</b> #{order['id']}\n\n"

        f"🐾 <b>Товар:</b> {order['product']}\n"
        f"🎨 <b>Цвет:</b> {order['color']}\n"
        f"💰 <b>Цена:</b> {order['price']:,} ₽\n\n"

        f"👤 <b>Клиент:</b> {order['client_name']}\n"
        f"💬 <b>Telegram:</b> {order['username']}\n"
        f"📱 <b>Телефон:</b> {order['phone']}\n"
        f"📍 <b>Адрес:</b> {order['address']}\n\n"

        "✅ Статус: заказ принят"
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

    # Сообщение клиенту
    try:
        await bot.send_message(
            order["client_id"],
            (
                "🎉 <b>Ваш заказ принят!</b>\n\n"
                f"🔖 Заказ: <b>#{order['id']}</b>\n"
                f"🐾 {order['product']}\n"
                f"🎨 {order['color']}\n"
                f"💰 {order['price']:,} ₽\n\n"
                "Мы свяжемся с вами для подтверждения "
                "деталей и оплаты. 🐾"
            ).replace(",", " "),
            parse_mode="HTML"
        )
    except Exception as error:
        logger.error(
            "Could not notify client %s: %s",
            order["client_id"],
            error
        )


# ============================================================
# АДМИН: ОТКЛОНИТЬ ЗАКАЗ
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

        f"🔖 <b>Заказ:</b> #{order['id']}\n\n"

        f"🐾 <b>Товар:</b> {order['product']}\n"
        f"🎨 <b>Цвет:</b> {order['color']}\n"
        f"💰 <b>Цена:</b> {order['price']:,} ₽\n\n"

        f"👤 <b>Клиент:</b> {order['client_name']}\n"
        f"📱 <b>Телефон:</b> {order['phone']}\n"
        f"📍 <b>Адрес:</b> {order['address']}\n\n"

        "❌ Статус: заказ отклонён"
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

    # Сообщение клиенту
    try:
        await bot.send_message(
            order["client_id"],
            (
                "❌ <b>К сожалению, мы не можем принять этот заказ.</b>\n\n"
                f"🔖 Номер заказа: <b>#{order['id']}</b>\n\n"
                "Пожалуйста, свяжитесь с нами — мы постараемся "
                "помочь вам оформить заказ."
            ),
            parse_mode="HTML"
        )
    except Exception as error:
        logger.error(
            "Could not notify client %s: %s",
            order["client_id"],
            error
        )


# ============================================================
# О МАГАЗИНЕ
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

        "UTTA — бренд стильных аксессуаров для собак. 🐾\n\n"

        "Мы создаём аксессуары, которые сочетают "
        "эстетику, комфорт и качество.\n\n"

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
# СВЯЗАТЬСЯ
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

    # ВАЖНО:
    # Здесь можно заменить username администратора
    # на свой.
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
# НЕИЗВЕСТНЫЕ КОМАНДЫ / СООБЩЕНИЯ
# ============================================================

@dp.message_handler(
    state="*"
)
async def unknown_message(
    message: types.Message,
    state: FSMContext
):

    # Если пользователь находится внутри оформления заказа,
    # не перехватываем сообщение.
    current_state = await state.get_state()

    if current_state:
        return

    await message.answer(
        "🐾 Выберите действие в меню ниже.",
        reply_markup=main_keyboard()
    )


# ============================================================
# ЗАПУСК
# ============================================================

async def on_startup(dispatcher):
    logger.info("====================================")
    logger.info("UTTA BOT STARTING")
    logger.info("Admin ID: %s", ADMIN_ID)
    logger.info("====================================")

    # Удаляем старые необработанные обновления.
    # Это особенно важно после перезапуска Render,
    # чтобы бот не обрабатывал старые сообщения повторно.
    try:
        await bot.delete_webhook(
            drop_pending_updates=True
        )
    except Exception as error:
        logger.warning(
            "Could not clear pending updates: %s",
            error
        )

    logger.info("UTTA BOT IS READY")


async def on_shutdown(dispatcher):
    logger.info("UTTA BOT STOPPING")

    await storage.close()
    await storage.wait_closed()

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
