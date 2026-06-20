from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.callback_data import CallbackData
from loader import db

product_cb = CallbackData('product', 'id', 'action')
search_cb = CallbackData('search', 'action', 'page')
favorite_cb = CallbackData('fav', 'id', 'action')
review_cb = CallbackData('review', 'id', 'action')
order_cb = CallbackData('order', 'id', 'action')
rating_cb = CallbackData('rating', 'id', 'value')


def product_markup(idx='', price=0, is_fav=False):

    global product_cb

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(f'Добавить в корзину - {price}₽', callback_data=product_cb.new(id=idx, action='add')))
    fav_text = '⭐ Убрать из избранного' if is_fav else '☆ В избранное'
    markup.add(InlineKeyboardButton(fav_text, callback_data=favorite_cb.new(id=idx, action='toggle')))
    markup.add(InlineKeyboardButton('💬 Отзывы', callback_data=review_cb.new(id=idx, action='list')))
    return markup


def product_detail_markup(idx='', price=0, is_fav=False, can_review=False, has_reviewed=False):

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(f'Добавить в корзину - {price}₽', callback_data=product_cb.new(id=idx, action='add')))
    fav_text = '⭐ Убрать из избранного' if is_fav else '☆ В избранное'
    markup.add(InlineKeyboardButton(fav_text, callback_data=favorite_cb.new(id=idx, action='toggle')))
    if can_review and not has_reviewed:
        markup.add(InlineKeyboardButton('✍️ Написать отзыв', callback_data=review_cb.new(id=idx, action='write')))
    markup.add(InlineKeyboardButton('💬 Отзывы', callback_data=review_cb.new(id=idx, action='list')))
    return markup


def search_pagination_markup(page, total_pages, keyword):
    markup = InlineKeyboardMarkup()
    buttons = []
    if page > 1:
        buttons.append(InlineKeyboardButton('⬅️ Назад', callback_data=search_cb.new(action='prev', page=str(page))))
    if page < total_pages:
        buttons.append(InlineKeyboardButton('Вперёд ➡️', callback_data=search_cb.new(action='next', page=str(page))))
    if buttons:
        markup.row(*buttons)
    markup.add(InlineKeyboardButton('🔙 К поиску', callback_data=search_cb.new(action='back', page='1')))
    return markup


def rating_markup(product_idx):
    markup = InlineKeyboardMarkup()
    row = []
    for i in range(1, 6):
        row.append(InlineKeyboardButton(f'{i}⭐', callback_data=rating_cb.new(id=product_idx, value=str(i))))
    markup.row(*row)
    return markup


def order_status_markup(order_id):
    from utils.db.storage import ORDER_STATUS_PENDING, ORDER_STATUS_SHIPPED, ORDER_STATUS_DELIVERED, ORDER_STATUS_CANCELLED, ORDER_STATUS_MAP
    markup = InlineKeyboardMarkup()
    for status_key, status_text in ORDER_STATUS_MAP.items():
        markup.add(InlineKeyboardButton(status_text, callback_data=order_cb.new(id=str(order_id), action=status_key)))
    return markup


def favorites_product_markup(idx, price):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(f'Добавить в корзину - {price}₽', callback_data=product_cb.new(id=idx, action='add')))
    markup.add(InlineKeyboardButton('⭐ Убрать из избранного', callback_data=favorite_cb.new(id=idx, action='remove')))
    return markup