import sqlite3
import calendar
from datetime import datetime, date
from config import DB_NAME

def get_conn():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_db():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            action TEXT,
            amount INTEGER,
            date DATE,
            time TIME,
            note TEXT
        )
    ''')
    conn.commit()
    conn.close()

def get_summary_report(chat_id):
    """重構後的統計函數：一次計算今日、本月、結餘與風控"""
    conn = get_conn()
    cursor = conn.cursor()
    
    now = datetime.now()
    today = date.today().strftime("%Y-%m-%d")
    month_start = date(now.year, now.month, 1)
    month_end = date(now.year, now.month, calendar.monthrange(now.year, now.month)[1])

    def query(sql, params):
        cursor.execute(sql, params)
        res = cursor.fetchone()
        return res[0] if res and res[0] is not None else 0

    # 1. 本月統計
    add_count = query('SELECT COUNT(*) FROM transactions WHERE action="add" AND chat_id=? AND date BETWEEN ? AND ?', (chat_id, month_start, month_end))
    sub_count = query('SELECT COUNT(*) FROM transactions WHERE action="subtract" AND chat_id=? AND date BETWEEN ? AND ?', (chat_id, month_start, month_end))
    add_total = query('SELECT SUM(amount) FROM transactions WHERE action="add" AND chat_id=? AND date BETWEEN ? AND ?', (chat_id, month_start, month_end))
    sub_total = query('SELECT SUM(amount) FROM transactions WHERE action="subtract" AND chat_id=? AND date BETWEEN ? AND ?', (chat_id, month_start, month_end))
    fee_total = query('SELECT SUM(amount) FROM transactions WHERE action="fee" AND chat_id=? AND date BETWEEN ? AND ?', (chat_id, month_start, month_end))
    last_month_count = query('SELECT SUM(amount) FROM transactions WHERE action="count" AND chat_id=? AND date BETWEEN ? AND ?', (chat_id, month_start, month_end))
    
    # 2. 今日統計
    add_today_total = query('SELECT SUM(amount) FROM transactions WHERE action="add" AND date=? AND chat_id=?', (today, chat_id))
    sub_today_total = query('SELECT SUM(amount) FROM transactions WHERE action="subtract" AND date=? AND chat_id=?', (today, chat_id))
    add_today_count = query('SELECT COUNT(*) FROM transactions WHERE action="add" AND date=? AND chat_id=?', (today, chat_id))
    sub_today_count = query('SELECT COUNT(*) FROM transactions WHERE action="subtract" AND date=? AND chat_id=?', (today, chat_id))
    
    # 3. 累計風控
    lock_total = query('SELECT SUM(amount) FROM transactions WHERE action="lock" AND chat_id=?', (chat_id,))

    # 4. 總計計算
    total = add_total - sub_total - fee_total + last_month_count - lock_total
    conn.close()

    return (f"本日:\n入{add_today_count}筆:{add_today_total},出{sub_today_count}筆:{sub_today_total}\n"
            f"本月:\n入{add_count}筆:{add_total},出{sub_count}筆:{sub_total}\n"
            f"手續費月計:{fee_total}\n風控:{lock_total}\n前期結餘:{last_month_count}\n"
            f"總計:{total}\n(月計-月計手續費+前期結餘)")
