from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from config import TOKEN, ADMIN_ID

bot = Bot(token=TOKEN)
dp = Dispatcher()

PRODUCT_NAME = "Премиальный поводок UTTA"
PRODUCT_PRICE = 2000
COLORS = {"pink": "🩷 Розовый", "blue": "💙 Голубой", "green": "💚 Салатовый"}

class OrderState(StatesGroup):
    choosing_color = State()
    waiting_phone = State()
    waiting_address = State()

def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛍 Каталог", callback_data="catalog")],
        [InlineKeyboardButton(text="ℹ️ О магазине", callback_data="about"),
         InlineKeyboardButton(text="📩 Связаться", callback_data="contact")]
    ])

def catalog_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🩷 Розовый", callback_data="color:pink")],
        [InlineKeyboardButton(text="💙 Голубой", callback_data="color:blue")],
        [InlineKeyboardButton(text="💚 Салатовый", callback_data="color:green")],
        [InlineKeyboardButton(text="⬅️ В меню", callback_data="menu")]
    ])

def product_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Оформить заказ", callback_data="order")],
        [InlineKeyboardButton(text="🎨 Выбрать другой цвет", callback_data="catalog")],
        [InlineKeyboardButton(text="⬅️ В меню", callback_data="menu")]
    ])

@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🐶 Добро пожаловать в магазин UTTA!\n\n"
        "Премиальные аксессуары для собак.\n\nВыберите раздел:",
        reply_markup=main_menu()
    )

@dp.callback_query(F.data == "menu")
async def menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("🐶 UTTA — премиальные аксессуары для собак.\n\nВыберите раздел:", reply_markup=main_menu())
    await callback.answer()

@dp.callback_query(F.data == "catalog")
async def catalog(callback: CallbackQuery, state: FSMContext):
    await state.set_state(OrderState.choosing_color)
    await callback.message.edit_text(
        f"🛍 КАТАЛОГ UTTA\n\n{PRODUCT_NAME}\nЦена: {PRODUCT_PRICE:,} ₽\n\nВыберите цвет:",
        reply_markup=catalog_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("color:"))
async def choose_color(callback: CallbackQuery, state: FSMContext):
    color = COLORS.get(callback.data.split(":", 1)[1])
    if not color:
        await callback.answer("Цвет не найден", show_alert=True)
        return
    await state.update_data(color=color)
    await state.set_state(OrderState.choosing_color)
    await callback.message.edit_text(
        f"🐾 ВАШ ТОВАР\n\n{PRODUCT_NAME}\nЦвет: {color}\nЦена: {PRODUCT_PRICE:,} ₽\n\nГотовы оформить заказ?",
        reply_markup=product_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "order")
async def start_order(callback: CallbackQuery, state: FSMContext):
    if not (await state.get_data()).get("color"):
        await callback.answer("Сначала выберите цвет", show_alert=True)
        return
    await state.set_state(OrderState.waiting_phone)
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Отправить номер телефона", request_contact=True)]],
        resize_keyboard=True, one_time_keyboard=True
    )
    await callback.message.answer(
        "🛒 Оформление заказа\n\nНажмите кнопку ниже, чтобы отправить номер телефона.",
        reply_markup=keyboard
    )
    await callback.answer()

@dp.message(OrderState.waiting_phone, F.contact)
async def receive_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.contact.phone_number)
    await state.set_state(OrderState.waiting_address)
    await message.answer("Спасибо! 👍\n\nТеперь напишите адрес доставки одним сообщением.", reply_markup=ReplyKeyboardRemove())

@dp.message(OrderState.waiting_phone, F.text)
async def phone_text(message: Message):
    await message.answer("Пожалуйста, используйте кнопку «📱 Отправить номер телефона».")

@dp.message(OrderState.waiting_address, F.text)
async def receive_address(message: Message, state: FSMContext):
    address = message.text.strip()
    if len(address) < 5:
        await message.answer("Пожалуйста, укажите полный адрес доставки.")
        return
    data = await state.get_data()
    username = f"@{message.from_user.username}" if message.from_user.username else "без username"
    order_text = (
        "🆕 НОВЫЙ ЗАКАЗ UTTA\n\n"
        f"Товар: {PRODUCT_NAME}\nЦвет: {data.get('color', 'Не указан')}\nЦена: {PRODUCT_PRICE:,} ₽\n\n"
        f"Клиент: {message.from_user.full_name}\nTelegram: {username}\n"
        f"Телефон: {data.get('phone', 'Не указан')}\nАдрес: {address}"
    )
    if ADMIN_ID:
        await bot.send_message(ADMIN_ID, order_text)
    await state.clear()
    await message.answer("✅ Заказ принят!\n\nМы свяжемся с вами для подтверждения и оплаты.", reply_markup=main_menu())

@dp.callback_query(F.data == "about")
async def about(callback: CallbackQuery):
    await callback.message.edit_text(
        "🐶 О UTTA\n\nUTTA — бренд стильных аксессуаров для собак.\n\n"
        "Сейчас доступны премиальные поводки в трёх цветах.\n\nСтоимость поводка — 2 000 ₽.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛍 Каталог", callback_data="catalog")],
            [InlineKeyboardButton(text="⬅️ В меню", callback_data="menu")]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == "contact")
async def contact(callback: CallbackQuery):
    await callback.message.edit_text(
        "📩 Связаться с UTTA\n\nПо вопросам заказа напишите нам в Telegram.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ В меню", callback_data="menu")]
        ])
    )
    await callback.answer()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
