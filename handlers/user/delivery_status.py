
import time
from aiogram.types import Message
from loader import dp, db
from .menu import delivery_status
from filters import IsUser
from utils.db.storage import ORDER_STATUS_MAP


@dp.message_handler(IsUser(), text=delivery_status)
async def process_delivery_status(message: Message):
    
    orders = db.get_user_orders(message.chat.id)
    
    if len(orders) == 0:
        await message.answer('У вас нет активных заказов.')
    else:
        await delivery_status_answer(message, orders)


async def delivery_status_answer(message, orders):

    res = ''

    for order in orders:
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

        product_items = []
        for item in products.split():
            if '=' in item:
                idx, qty = item.split('=')
                product = db.fetchone('SELECT title, price FROM products WHERE idx=?', (idx,))
                if product:
                    product_items.append(f'{product[0]} × {qty} ({product[1]}₽)')

        products_text = '\n'.join(product_items) if product_items else products

        res += f'<b>Заказ №{rowid}</b>\n'
        res += f'📦 Статус: {status_text}\n'
        res += f'🕐 Время: {time_text}\n'
        res += f'👤 Имя: {usr_name}\n'
        res += f'📍 Адрес: {usr_address}\n'
        res += f'🛒 Товары:\n{products_text}\n\n'

    await message.answer(res)
