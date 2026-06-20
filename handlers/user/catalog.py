
import logging
import time
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.dispatcher import FSMContext
from keyboards.inline.categories import categories_markup, category_cb
from keyboards.inline.products_from_catalog import (
    product_markup, product_cb, product_detail_markup,
    search_cb, favorite_cb, review_cb, rating_cb,
    search_pagination_markup, rating_markup
)
from aiogram.types.chat import ChatActions
from loader import dp, db, bot
from .menu import catalog
from filters import IsUser
from states import SearchState, ReviewState
from keyboards.default.markups import cancel_message, search_cancel_markup, back_message


@dp.message_handler(IsUser(), text=catalog)
async def process_catalog(message: Message):
    await message.answer('Выберите раздел, чтобы вывести список товаров:',
                         reply_markup=categories_markup())


@dp.callback_query_handler(IsUser(), category_cb.filter(action='view'))
async def category_callback_handler(query: CallbackQuery, callback_data: dict):

    products = db.fetchall('''SELECT * FROM products product
    WHERE product.tag = (SELECT title FROM categories WHERE idx=?) 
    AND product.idx NOT IN (SELECT idx FROM cart WHERE cid = ?)''',
                           (callback_data['id'], query.message.chat.id))

    await query.answer('Все доступные товары.')
    await show_products(query.message, products, query.message.chat.id)


@dp.callback_query_handler(IsUser(), product_cb.filter(action='add'))
async def add_product_callback_handler(query: CallbackQuery, callback_data: dict):

    db.query('INSERT INTO cart VALUES (?, ?, 1)',
             (query.message.chat.id, callback_data['id']))

    await query.answer('Товар добавлен в корзину!')
    await query.message.delete()


@dp.message_handler(IsUser(), text='🔍 Поиск товаров')
async def process_search_start(message: Message, state: FSMContext):
    await SearchState.keyword.set()
    await message.answer('Введите ключевое слово для поиска товаров:',
                         reply_markup=search_cancel_markup())


@dp.message_handler(IsUser(), text=cancel_message, state=SearchState.keyword)
async def process_search_cancel(message: Message, state: FSMContext):
    await state.finish()
    await message.answer('Поиск отменён.', reply_markup=ReplyKeyboardRemove())


@dp.message_handler(IsUser(), state=SearchState.keyword)
async def process_search_keyword(message: Message, state: FSMContext):
    keyword = message.text.strip()
    if not keyword:
        await message.answer('Введите непустой запрос.')
        return
    products, total_pages, total = db.search_products(keyword, page=1, per_page=5)
    if total == 0:
        await state.finish()
        await message.answer(f'По запросу "{keyword}" ничего не найдено.',
                             reply_markup=ReplyKeyboardRemove())
        return
    async with state.proxy() as data:
        data['search_keyword'] = keyword
    await show_search_results(message, products, keyword, 1, total_pages, total, state)


async def show_search_results(message, products, keyword, page, total_pages, total, state):
    await bot.send_chat_action(message.chat.id, ChatActions.TYPING)
    cid = message.chat.id
    for p in products:
        idx, title, body, image, price, _tag = p[0], p[1], p[2], p[3], p[4], p[5]
        is_fav = db.is_favorite(cid, idx)
        rating_avg = db.get_product_rating_avg(idx)
        rating_text = f'\n\n⭐ Средняя оценка: {rating_avg:.1f}' if rating_avg > 0 else ''
        markup = product_markup(idx, price, is_fav)
        text = f'<b>{title}</b>\n\n{body}{rating_text}'
        await message.answer_photo(photo=image, caption=text, reply_markup=markup)

    pag_markup = search_pagination_markup(page, total_pages, keyword)
    await message.answer(
        f'Найдено товаров: {total} | Страница {page}/{total_pages}',
        reply_markup=pag_markup
    )


@dp.callback_query_handler(IsUser(), search_cb.filter())
async def search_pagination_handler(query: CallbackQuery, callback_data: dict, state: FSMContext):
    action = callback_data['action']
    current_page = int(callback_data['page'])
    async with state.proxy() as data:
        keyword = data.get('search_keyword', '')

    if action == 'back':
        await query.message.delete()
        await SearchState.keyword.set()
        await query.message.answer('Введите ключевое слово для поиска:',
                                   reply_markup=search_cancel_markup())
        return

    if action == 'prev':
        new_page = max(1, current_page - 1)
    elif action == 'next':
        new_page = current_page + 1
    else:
        new_page = current_page

    products, total_pages, total = db.search_products(keyword, page=new_page, per_page=5)
    await query.message.delete()
    await show_search_results(query.message, products, keyword, new_page, total_pages, total, state)


@dp.callback_query_handler(IsUser(), favorite_cb.filter())
async def favorite_toggle_handler(query: CallbackQuery, callback_data: dict):
    product_idx = callback_data['id']
    action = callback_data['action']
    cid = query.message.chat.id

    if action == 'toggle':
        if db.is_favorite(cid, product_idx):
            db.remove_favorite(cid, product_idx)
            await query.answer('Убрано из избранного')
        else:
            db.add_favorite(cid, product_idx)
            await query.answer('Добавлено в избранное!')
    elif action == 'remove':
        db.remove_favorite(cid, product_idx)
        await query.answer('Убрано из избранного')
        await query.message.delete()

    product = db.fetchone('SELECT * FROM products WHERE idx=?', (product_idx,))
    if product:
        is_fav = db.is_favorite(cid, product_idx)
        rating_avg = db.get_product_rating_avg(product_idx)
        can_review = db.has_purchased_product(cid, product_idx)
        has_reviewed = db.has_reviewed(cid, product_idx)
        new_markup = product_detail_markup(product_idx, product[4], is_fav, can_review, has_reviewed)
        try:
            await query.message.edit_reply_markup(new_markup)
        except Exception:
            pass


@dp.callback_query_handler(IsUser(), review_cb.filter(action='list'))
async def review_list_handler(query: CallbackQuery, callback_data: dict):
    product_idx = callback_data['id']
    product = db.fetchone('SELECT idx, title FROM products WHERE idx=?', (product_idx,))
    if not product:
        await query.answer('Товар не найден')
        return
    reviews = db.get_product_reviews(product_idx, limit=5)
    rating_avg = db.get_product_rating_avg(product_idx)

    res = f'<b>Отзывы на "{product[1]}"</b>\n'
    res += f'⭐ Средняя оценка: {rating_avg:.1f}\n\n'
    if not reviews:
        res += 'Пока нет отзывов.'
    else:
        for cid, rating, comment, created_at in reviews:
            t = time.strftime('%Y-%m-%d %H:%M', time.localtime(created_at or 0))
            stars = '⭐' * rating
            comment_text = comment[:500]
            res += f'{stars} ({rating}/5) — {t}\n{comment_text}\n\n'

    await query.answer('Отзывы')
    await query.message.answer(res)


@dp.callback_query_handler(IsUser(), review_cb.filter(action='write'))
async def review_write_handler(query: CallbackQuery, callback_data: dict, state: FSMContext):
    product_idx = callback_data['id']
    cid = query.message.chat.id
    if not db.has_purchased_product(cid, product_idx):
        await query.answer('Вы можете оставить отзыв только на купленный товар')
        return
    if db.has_reviewed(cid, product_idx):
        await query.answer('Вы уже оставляли отзыв на этот товар')
        return
    async with state.proxy() as data:
        data['review_product_idx'] = product_idx
    await ReviewState.rating.set()
    await query.answer('Напишите отзыв')
    await query.message.answer('Поставьте оценку от 1 до 5 звёзд:',
                               reply_markup=rating_markup(product_idx))


@dp.callback_query_handler(IsUser(), rating_cb.filter(), state=ReviewState.rating)
async def review_rating_handler(query: CallbackQuery, callback_data: dict, state: FSMContext):
    rating = int(callback_data['value'])
    product_idx = callback_data['id']
    async with state.proxy() as data:
        data['review_rating'] = rating
        data['review_product_idx'] = product_idx
    await ReviewState.next()
    await query.answer(f'Оценка: {rating}⭐')
    await query.message.answer('Введите текст отзыва (до 500 символов):',
                               reply_markup=ReplyKeyboardRemove())


@dp.message_handler(IsUser(), state=ReviewState.rating)
async def review_rating_text(message: Message, state: FSMContext):
    text = message.text.strip()
    if text.isdigit() and 1 <= int(text) <= 5:
        async with state.proxy() as data:
            data['review_rating'] = int(text)
        await ReviewState.next()
        await message.answer('Введите текст отзыва (до 500 символов):',
                             reply_markup=ReplyKeyboardRemove())
    else:
        await message.answer('Введите число от 1 до 5.')


@dp.message_handler(IsUser(), state=ReviewState.comment)
async def review_comment_handler(message: Message, state: FSMContext):
    comment = message.text.strip()
    if len(comment) > 500:
        await message.answer(f'Комментарий слишком длинный ({len(comment)} / 500 символов). Сократите, пожалуйста.')
        return
    if not comment:
        await message.answer('Комментарий не может быть пустым.')
        return
    async with state.proxy() as data:
        product_idx = data.get('review_product_idx')
        rating = data.get('review_rating', 5)
    if not product_idx:
        await state.finish()
        await message.answer('Ошибка: товар не найден.')
        return
    cid = message.chat.id
    db.add_review(product_idx, cid, rating, comment)
    await state.finish()
    await message.answer(f'Спасибо! Ваш отзыв принят: {rating}⭐')


async def show_products(m, products, cid=None):

    if len(products) == 0:
        await m.answer('Здесь ничего нет 😢')
    else:
        await bot.send_chat_action(m.chat.id, ChatActions.TYPING)
        cid = cid or m.chat.id
        for product in products:
            idx, title, body, image, price, _ = product[0], product[1], product[2], product[3], product[4], product[5]
            is_fav = db.is_favorite(cid, idx)
            rating_avg = db.get_product_rating_avg(idx)
            rating_text = f'\n\n⭐ Средняя оценка: {rating_avg:.1f}' if rating_avg > 0 else ''
            markup = product_markup(idx, price, is_fav)
            text = f'<b>{title}</b>\n\n{body}{rating_text}'
            await m.answer_photo(photo=image,
                                 caption=text,
                                 reply_markup=markup)
