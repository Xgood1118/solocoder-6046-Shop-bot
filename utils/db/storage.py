
import sqlite3 as lite
import time

ORDER_STATUS_PENDING = 'pending'
ORDER_STATUS_SHIPPED = 'shipped'
ORDER_STATUS_DELIVERED = 'delivered'
ORDER_STATUS_CANCELLED = 'cancelled'

ORDER_STATUS_MAP = {
    ORDER_STATUS_PENDING: '待付款',
    ORDER_STATUS_SHIPPED: '已发货',
    ORDER_STATUS_DELIVERED: '已送达',
    ORDER_STATUS_CANCELLED: '已取消',
}

class DatabaseManager(object):

    def __init__(self, path):
        self.conn = lite.connect(path)
        self.conn.execute('pragma foreign_keys = on')
        self.conn.commit()
        self.cur = self.conn.cursor()

    def create_tables(self):
        self.query('CREATE TABLE IF NOT EXISTS products (idx text, title text, body text, photo blob, price int, tag text)')
        self.query('CREATE TABLE IF NOT EXISTS orders (cid int, usr_name text, usr_address text, products text)')
        self.query('CREATE TABLE IF NOT EXISTS cart (cid int, idx text, quantity int)')
        self.query('CREATE TABLE IF NOT EXISTS categories (idx text, title text)')
        self.query('CREATE TABLE IF NOT EXISTS wallet (cid int, balance real)')
        self.query('CREATE TABLE IF NOT EXISTS questions (cid int, question text)')
        self.migrate()

    def migrate(self):
        try:
            self.cur.execute('ALTER TABLE orders ADD COLUMN status TEXT DEFAULT ?', (ORDER_STATUS_PENDING,))
        except lite.OperationalError:
            pass
        try:
            self.cur.execute('ALTER TABLE orders ADD COLUMN created_at INTEGER')
        except lite.OperationalError:
            pass
        try:
            self.cur.execute('ALTER TABLE products ADD COLUMN rating_avg REAL DEFAULT 0')
        except lite.OperationalError:
            pass
        self.query('CREATE TABLE IF NOT EXISTS favorites (cid int, product_idx text, PRIMARY KEY (cid, product_idx))')
        self.query('CREATE TABLE IF NOT EXISTS reviews (id INTEGER PRIMARY KEY AUTOINCREMENT, product_idx text, cid int, rating int, comment text, created_at INTEGER)')
        self.conn.commit()
        self._migrate_orders_timestamps()
        self._migrate_orders_status()

    def _migrate_orders_timestamps(self):
        rows = self.fetchall('SELECT rowid, created_at FROM orders WHERE created_at IS NULL')
        now = int(time.time())
        for i, (rowid, _) in enumerate(rows):
            approx_time = now - (len(rows) - i) * 86400
            self.query('UPDATE orders SET created_at = ? WHERE rowid = ?', (approx_time, rowid))

    def _migrate_orders_status(self):
        self.query(f"UPDATE orders SET status = ? WHERE status IS NULL OR status = ''", (ORDER_STATUS_PENDING,))

    def query(self, arg, values=None):
        if values == None:
            self.cur.execute(arg)
        else:
            self.cur.execute(arg, values)
        self.conn.commit()

    def fetchone(self, arg, values=None):
        if values == None:
            self.cur.execute(arg)
        else:
            self.cur.execute(arg, values)
        return self.cur.fetchone()

    def fetchall(self, arg, values=None):
        if values == None:
            self.cur.execute(arg)
        else:
            self.cur.execute(arg, values)
        return self.cur.fetchall()

    def search_products(self, keyword, page=1, per_page=5):
        offset = (page - 1) * per_page
        like = f'%{keyword}%'
        products = self.fetchall(
            'SELECT * FROM products WHERE title LIKE ? LIMIT ? OFFSET ?',
            (like, per_page, offset)
        )
        total = self.fetchone('SELECT COUNT(*) FROM products WHERE title LIKE ?', (like,))[0]
        total_pages = (total + per_page - 1) // per_page if total > 0 else 0
        return products, total_pages, total

    def add_favorite(self, cid, product_idx):
        try:
            self.query('INSERT INTO favorites (cid, product_idx) VALUES (?, ?)', (cid, product_idx))
            return True
        except lite.IntegrityError:
            return False

    def remove_favorite(self, cid, product_idx):
        self.query('DELETE FROM favorites WHERE cid = ? AND product_idx = ?', (cid, product_idx))

    def is_favorite(self, cid, product_idx):
        return self.fetchone('SELECT 1 FROM favorites WHERE cid = ? AND product_idx = ?', (cid, product_idx)) is not None

    def get_favorites(self, cid):
        return self.fetchall('''
            SELECT p.* FROM products p
            INNER JOIN favorites f ON p.idx = f.product_idx
            WHERE f.cid = ?
        ''', (cid,))

    def get_user_orders(self, cid):
        return self.fetchall('SELECT rowid, * FROM orders WHERE cid = ? ORDER BY COALESCE(created_at, 0) DESC', (cid,))

    def get_all_orders(self):
        return self.fetchall('SELECT rowid, * FROM orders ORDER BY COALESCE(created_at, 0) DESC')

    def get_order_by_rowid(self, rowid):
        return self.fetchone('SELECT rowid, * FROM orders WHERE rowid = ?', (rowid,))

    def update_order_status(self, rowid, status):
        self.query('UPDATE orders SET status = ? WHERE rowid = ?', (status, rowid))

    def add_review(self, product_idx, cid, rating, comment):
        now = int(time.time())
        self.query(
            'INSERT INTO reviews (product_idx, cid, rating, comment, created_at) VALUES (?, ?, ?, ?, ?)',
            (product_idx, cid, rating, comment, now)
        )
        self._update_product_rating_avg(product_idx)

    def _update_product_rating_avg(self, product_idx):
        avg = self.fetchone('SELECT AVG(rating) FROM reviews WHERE product_idx = ?', (product_idx,))[0]
        if avg is None:
            avg = 0
        self.query('UPDATE products SET rating_avg = ? WHERE idx = ?', (avg, product_idx))

    def get_product_reviews(self, product_idx, limit=5):
        return self.fetchall(
            'SELECT cid, rating, comment, created_at FROM reviews WHERE product_idx = ? ORDER BY created_at DESC LIMIT ?',
            (product_idx, limit)
        )

    def get_product_rating_avg(self, product_idx):
        row = self.fetchone('SELECT rating_avg FROM products WHERE idx = ?', (product_idx,))
        return row[0] if row and row[0] is not None else 0

    def has_purchased_product(self, cid, product_idx):
        orders = self.fetchall('SELECT products FROM orders WHERE cid = ?', (cid,))
        for (products_str,) in orders:
            items = products_str.split()
            for item in items:
                idx = item.split('=')[0]
                if idx == product_idx:
                    return True
        return False

    def has_reviewed(self, cid, product_idx):
        return self.fetchone('SELECT 1 FROM reviews WHERE cid = ? AND product_idx = ?', (cid, product_idx)) is not None

    def __del__(self):
        self.conn.close()


'''

products: idx text, title text, body text, photo blob, price int, tag text

orders: cid int, usr_name text, usr_address text, products text

cart: cid int, idx text, quantity int ==> product_idx

categories: idx text, title text

wallet: cid int, balance real

questions: cid int, question text

'''
