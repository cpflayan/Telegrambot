import re
import logging
import sqlite3
import calendar
import pandas as pd
from datetime import datetime, date, timedelta
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackContext

# 設置日志
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# 定義不同的狀態
START, ADD, SUBTRACT = range(3)

# 建立數據庫連接
conn = sqlite3.connect('bank.db', check_same_thread = False)
cursor = conn.cursor()

# 創建表格
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
#tz = pytz.timezone('Asia/Taipei')
#now = datetime.now(tz)

# 啟動命令處理器
def start(update: Update, context: CallbackContext) -> int:
    update.message.reply_text("歡迎使用入/出機器人！")
    return START

# 處理入金
def add(update: Update, context: CallbackContext) -> int:
        now = datetime.now()
        currentDate = now.strftime("%Y-%m-%d")
        currentTime = now.strftime("%H:%M:%S")
        current_month_start = datetime(now.year, now.month, 1)
        current_month_end = datetime(now.year, now.month, calendar.monthrange(now.year, now.month)[1])
        today = date.today().strftime("%Y-%m-%d")

        chat_id = update.message.chat.id

        amount = int(context.args[0])
        cursor.execute('INSERT INTO transactions (chat_id, action, amount, date, time, note) VALUES (?, ?, ?, ?, ?, ?)', (chat_id, "add", amount, currentDate, currentTime, "入"))
        conn.commit()

        # 获取刚插入记录的 ID
        new_record_id = cursor.lastrowid

        cursor.execute('SELECT COUNT(*) FROM transactions WHERE action="add" AND chat_id = ? AND date BETWEEN ? AND ?', (chat_id, current_month_start, current_month_end))
        add_count = cursor.fetchone()[0] or 0

        cursor.execute('SELECT COUNT(*) FROM transactions WHERE action="subtract" AND chat_id = ? AND date BETWEEN ? AND ?', (chat_id, current_month_start, current_month_end))
        subtract_count = cursor.fetchone()[0] or 0

        cursor.execute('SELECT SUM(amount) FROM transactions WHERE action="add" AND chat_id = ? AND date BETWEEN ? AND ?', (chat_id, current_month_start, current_month_end))
        add_total = cursor.fetchone()[0] or 0

        cursor.execute('SELECT SUM(amount) FROM transactions WHERE action="subtract" AND chat_id = ? AND date BETWEEN ? AND ?', (chat_id, current_month_start, current_month_end))
        subtract_total = cursor.fetchone()[0] or 0

        cursor.execute('SELECT SUM(amount) FROM transactions WHERE action="add" AND date = ? AND chat_id = ?', (today, chat_id))
        add_today_total = cursor.fetchone()[0] or 0

        cursor.execute('SELECT SUM(amount) FROM transactions WHERE action="subtract" AND date = ? AND chat_id = ?', (today, chat_id))
        subtract_today_total = cursor.fetchone()[0] or 0

        cursor.execute('SELECT COUNT(*) FROM transactions WHERE action="add" AND date = ? AND chat_id = ?', (today, chat_id))
        add_today_count = cursor.fetchone()[0] or 0

        cursor.execute('SELECT COUNT(*) FROM transactions WHERE action="subtract" AND date = ? AND chat_id = ?', (today, chat_id))
        subtract_today_count = cursor.fetchone()[0] or 0

        cursor.execute('SELECT SUM(amount) FROM transactions WHERE action="fee" AND chat_id = ? AND date BETWEEN ? AND ?', (chat_id, current_month_start, current_month_end))
        fee_total = cursor.fetchone()[0] or 0

        cursor.execute('SELECT SUM(amount) FROM transactions WHERE action="count" AND chat_id = ? AND date BETWEEN ? AND ?', (chat_id, current_month_start, current_month_end))
        last_month_count = cursor.fetchone()[0] or 0

        total = add_total - subtract_total - fee_total + last_month_count
        context.bot.send_message(chat_id=chat_id, text=f"({new_record_id}) {currentDate} {currentTime} \n+{amount} \n\n------------------------------------------------\n本日:\n入{add_today_count}筆:{add_today_total},出{subtract_today_count}筆:{subtract_today_total}\n本月:\n入{add_count}筆:{add_total},出{subtract_count}筆:{subtract_total}\n手續費月計:{fee_total},前期結餘:{last_month_count}\n總計:{total}\n(月計-月計手續費+前期結餘)")
        return START

# 處理出金
def subtract(update: Update, context: CallbackContext) -> int:
        now = datetime.now()
        currentDate = now.strftime("%Y-%m-%d")
        currentTime = now.strftime("%H:%M:%S")
        current_month_start = datetime(now.year, now.month, 1)
        current_month_end = datetime(now.year, now.month, calendar.monthrange(now.year, now.month)[1])
        today = date.today().strftime("%Y-%m-%d")

        chat_id = update.message.chat.id

        amount = int(context.args[0])

        cursor.execute('INSERT INTO transactions (chat_id, action, amount, date, time, note) VALUES (?, ?, ?, ?, ?, ?)', (chat_id, "subtract", amount, currentDate, currentTime, "出"))
        conn.commit()

        # 獲取剛插入紀錄的 ID
        new_record_id = cursor.lastrowid

        cursor.execute('SELECT COUNT(*) FROM transactions WHERE action="add" AND chat_id = ? AND date BETWEEN ? AND ?', (chat_id, current_month_start, current_month_end))
        add_count = cursor.fetchone()[0] or 0

        cursor.execute('SELECT COUNT(*) FROM transactions WHERE action="subtract" AND chat_id = ? AND date BETWEEN ? AND ?', (chat_id, current_month_start, current_month_end))
        subtract_count = cursor.fetchone()[0] or 0

        cursor.execute('SELECT SUM(amount) FROM transactions WHERE action="add" AND chat_id = ? AND date BETWEEN ? AND ?', (chat_id, current_month_start, current_month_end))
        add_total = cursor.fetchone()[0] or 0

        cursor.execute('SELECT SUM(amount) FROM transactions WHERE action="subtract" AND chat_id = ? AND date BETWEEN ? AND ?', (chat_id, current_month_start, current_month_end))
        subtract_total = cursor.fetchone()[0] or 0

        cursor.execute('SELECT SUM(amount) FROM transactions WHERE action="add" AND date = ? AND chat_id = ?', (today, chat_id))
        add_today_total = cursor.fetchone()[0] or 0

        cursor.execute('SELECT SUM(amount) FROM transactions WHERE action="subtract" AND date = ? AND chat_id = ?', (today, chat_id))
        subtract_today_total = cursor.fetchone()[0] or 0

        cursor.execute('SELECT COUNT(*) FROM transactions WHERE action="add" AND date = ? AND chat_id = ?', (today, chat_id))
        add_today_count = cursor.fetchone()[0] or 0

        cursor.execute('SELECT COUNT(*) FROM transactions WHERE action="subtract" AND date = ? AND chat_id = ?', (today, chat_id))
        subtract_today_count = cursor.fetchone()[0] or 0

        cursor.execute('SELECT SUM(amount) FROM transactions WHERE action="fee" AND chat_id = ? AND date BETWEEN ? AND ?', (chat_id, current_month_start, current_month_end))
        fee_total = cursor.fetchone()[0] or 0

        cursor.execute('SELECT SUM(amount) FROM transactions WHERE action="count" AND chat_id = ? AND date BETWEEN ? AND ?', (chat_id, current_month_start, current_month_end))
        last_month_count = cursor.fetchone()[0] or 0

        total = add_total - subtract_total - fee_total + last_month_count
        context.bot.send_message(chat_id=chat_id, text=f"({new_record_id}) {currentDate} {currentTime} \n-{amount} \n\n------------------------------------------------\n本日:\n入{add_today_count}筆:{add_today_total},出{subtract_today_count}筆:{subtract_today_total}\n本月:\n入{add_count}筆:{add_total},出{subtract_count}筆:{subtract_total}\n手續費月計:{fee_total},前期結餘:{last_month_count}\n總計:{total}\n(月計-月計手續費+前期結餘)")
        return START

#新增手續費
def add_fee(update: Update, context: CallbackContext) -> int:
        chat_id = update.message.chat.id
        now = datetime.now()
        currentDate = now.strftime("%Y-%m-%d")
        currentTime = now.strftime("%H:%M:%S")
        current_month_start = datetime(now.year, now.month, 1)
        current_month_end = datetime(now.year, now.month, calendar.monthrange(now.year, now.month)[1])
        today = date.today().strftime("%Y-%m-%d")

        chat_id = update.message.chat.id

        amount = int(context.args[0])  # 假設用户提供金额作為参數
# 執行 INSERT 操作，插入新紀錄
        cursor.execute('INSERT INTO transactions (chat_id, action, amount, date, time, note) VALUES (?, ?, ?, ?, ?, ?)', (chat_id, "fee", amount, currentDate, currentTime, "手續費"))
        conn.commit()


# 獲取剛插入紀錄的 ID
        new_record_id = cursor.lastrowid

        cursor.execute('SELECT COUNT(*) FROM transactions WHERE action="add" AND chat_id = ? AND date BETWEEN ? AND ?', (chat_id, current_month_start, current_month_end))
        add_count = cursor.fetchone()[0] or 0

        cursor.execute('SELECT COUNT(*) FROM transactions WHERE action="subtract" AND chat_id = ? AND date BETWEEN ? AND ?', (chat_id, current_month_start, current_month_end))
        subtract_count = cursor.fetchone()[0] or 0

        cursor.execute('SELECT SUM(amount) FROM transactions WHERE action="add" AND chat_id = ? AND date BETWEEN ? AND ?', (chat_id, current_month_start, current_month_end))
        add_total = cursor.fetchone()[0] or 0

        cursor.execute('SELECT SUM(amount) FROM transactions WHERE action="subtract" AND chat_id = ? AND date BETWEEN ? AND ?', (chat_id, current_month_start, current_month_end))
        subtract_total = cursor.fetchone()[0] or 0

        cursor.execute('SELECT SUM(amount) FROM transactions WHERE action="add" AND date = ? AND chat_id = ?', (today, chat_id))
        add_today_total = cursor.fetchone()[0] or 0

        cursor.execute('SELECT SUM(amount) FROM transactions WHERE action="subtract" AND date = ? AND chat_id = ?', (today, chat_id))
        subtract_today_total = cursor.fetchone()[0] or 0

        cursor.execute('SELECT COUNT(*) FROM transactions WHERE action="add" AND date = ? AND chat_id = ?', (today, chat_id))
        add_today_count = cursor.fetchone()[0] or 0

        cursor.execute('SELECT COUNT(*) FROM transactions WHERE action="subtract" AND date = ? AND chat_id = ?', (today, chat_id))
        subtract_today_count = cursor.fetchone()[0] or 0


        cursor.execute('SELECT SUM(amount) FROM transactions WHERE acti