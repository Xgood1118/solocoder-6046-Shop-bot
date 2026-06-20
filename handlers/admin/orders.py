
import time
from aiogram.types import Message, CallbackQuery
from loader import dp, db, bot
from handlers.user.menu import orders
from filters import IsAdmin
from keyboards.inline.products_from_catalog import order_status_markup, order_cb
from utils.db.storage import ORDER_STATUS_MAP


@dp.message_handler(IsAdmin(), text=orders)
async def process_orders(message: Message):
    
    orders_list = db.get_all_orders()
    
    if len(orders_list) == 0:
        await message.answer('У вас нет заказов.')
    else:
        await order_answer(message, orders_list)


@dp.callback_query_handler(IsAdmin(), order_cb.filter())
async def order_status_change_handler(query: CallbackQuery, callback_data: dict):
    order_id = int(callback_data['id'])
    new_status = callback_data['action']
    order = db.get_order_by_rowid(order_id)
    if not order:
        await query.answer('Заказ не найден')
        return
    old_status = order[5] if len(order) > 5 else None
    db.update_order_status(order_id, new_status)
    status_text = ORDER_STATUS_MAP.get(new_status, new_status)
    await query.answer(f'Статус изменён на: {status_text}')

    cid = order[1]
    try:
        await bot.send_message(cid, f'📦 Статус вашего заказа №{order_id} изменён: <b>{status_text}</b>')
    except Exception:
        pass

    new_order = db.get_order_by_rowid(order_id)
    new_markup = order_status_markup(order_id)
    try:
        await query.message.edit_text(
            _format_order_text(new_order),
            reply_markup=new_markup
        )
    except Exception:
        pass


def _format_order_text(order):
    rowid = order[0]
    cid = order[1]
    usr_name = order[2]
    usr_address = order[3]
    products = order[4]
    status = order[5] if len(order) > 5 else 'pending'
    created_at = order[6] if len(order) > 6 else None

    status_text = ORDER_STATUS_MAP.get(status, '待付款')
    if created_at:
        time_text = time.strftime('%Y-%m-%d %H:%M', time.localtime(created_at))
    else:
        time_text = '—'

    res = f'<b>Заказ №{rowid}</b>\n'
    res += f'📦 Статус: {status_text}\n'
    res += f'🕐 Время: {time_text}\n'
    res += f'👤 Имя: {usr_name}\n'
    res += f'📍 Адрес: {usr_address}\n'
    res += f'🛒 Товары: {products}\n'
    return res


async def order_answer(message, orders_list):

    for order in orders_list:
        rowid = order[0]
        text = _format_order_text(order)
        markup = order_status_markup(rowid)
        await message.answer(text, reply_markup=markup)
