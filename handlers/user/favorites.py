from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.types.chat import ChatActions
from loader import dp, db, bot
from filters import IsUser
from .menu import favorites
from keyboards.inline.products_from_catalog import favorites_product_markup


@dp.message_handler(IsUser(), text=favorites)
async def process_favorites(message: Message):
    cid = message.chat.id
    products = db.get_favorites(cid)

    if len(products) == 0:
        await message.answer('Ваше избранное пока пусто.')
    else:
        await bot.send_chat_action(cid, ChatActions.TYPING)
        for p in products:
            idx, title, body, image, price, _tag = p[0], p[1], p[2], p[3], p[4], p[5]
            rating_avg = db.get_product_rating_avg(idx)
            rating_text = f'\n\n⭐ Средняя оценка: {rating_avg:.1f}' if rating_avg > 0 else ''
            markup = favorites_product_markup(idx, price)
            text = f'<b>{title}</b>\n\n{body}{rating_text}'
            await message.answer_photo(photo=image, caption=text, reply_markup=markup)
