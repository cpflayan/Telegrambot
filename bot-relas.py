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
        amount REAL,
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
    update.message.reply_text("/+  數字\n/-  數字\n/手續費  數字\n/刪除  編號  日期(/刪除 30 2023-01-01)\n/風控  數字\n/顯示\n/流量  日期(/流量 2023-01-01 or 2023-01)\n/列表  日期(/列表 2023-01-01 or 2023-01)\n/匯出  日期(/匯出 2023-01-01 or 2023-01)\n/結算  日期(/結算 2023-01)\n          　　結算並記錄 (/結算 2023-01record )")
    return START

# 處理入金
def add(update: Update, context: CallbackContext, amount) -> int:
        now = datetime.now()
        currentDate = now.strftime("%Y-%m-%d")
        currentTime = now.strftime("%H:%M:%S")
        current_month_start = date(now.year, now.month, 1)
        current_month_end = date(now.year, now.month, calendar.monthrange(now.year, now.month)[1])
        today = date.today().strftime("%Y-%m-%d")

        chat_id = update.message.chat.id
        #amount = int(message_text[3:])
        #amount = int(context.args[0])
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

        cursor.execute('SELECT SUM(amount) FROM transactions WHERE action="lock" AND chat_id = ?', (chat_id,))
        lock_total = cursor.fetchone()[0] or 0


        total = add_total - subtract_total - fee_total + last_month_count - lock_total
        context.bot.send_message(chat_id=chat_id, text=f"({new_record_id}) {currentDate} {currentTime} \n+{amount} \n\n------------------------------------------------\n本日:\n入{add_today_count}筆:{add_today_total},出{subtract_today_count}筆:{subtract_today_total}\n本月:\n入{add_count}筆:{add_total},出{subtract_count}筆:{subtract_total}\n手續費月計:{fee_total}\n風控:{lock_total}\n前期結餘:{last_month_count}\n總計:{total}\n(月計-月計手續費+前期結餘)")
        return START

# 處理出金
def subtract(update: Update, context: CallbackContext, amount) -> int:
        now = datetime.now()
        currentDate = now.strftime("%Y-%m-%d")
        currentTime = now.strftime("%H:%M:%S")
        current_month_start = date(now.year, now.month, 1)
        current_month_end = date(now.year, now.month, calendar.monthrange(now.year, now.month)[1])
        today = date.today().strftime("%Y-%m-%d")

        chat_id = update.message.chat.id

        #amount = int(context.args[0])

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

        cursor.execute('SELECT SUM(amount) FROM transactions WHERE action="lock" AND chat_id = ?', (chat_id,))
        lock_total = cursor.fetchone()[0] or 0


        total = add_total - subtract_total - fee_total + last_month_count - lock_total
        context.bot.send_message(chat_id=chat_id, text=f"({new_record_id}) {currentDate} {currentTime} \n-{amount} \n\n------------------------------------------------\n本日:\n入{add_today_count}筆:{add_today_total},出{subtract_today_count}筆:{subtract_today_total}\n本月:\n入{add_count}筆:{add_total},出{subtract_count}筆:{subtract_total}\n手續費月計:{fee_total}\n風控:{lock_total}\n前期結餘:{last_month_count}\n總計:{total}\n(月計-月計手續費+前期結餘)")
        return START


#新增手續費
def add_fee(update: Update, context: CallbackContext, amount) -> int:
        chat_id = update.message.chat.id
        now = datetime.now()
        currentDate = now.strftime("%Y-%m-%d")
        currentTime = now.strftime("%H:%M:%S")
        current_month_start = date(now.year, now.month, 1)
        current_month_end = date(now.year, now.month, calendar.monthrange(now.year, now.month)[1])
        today = date.today().strftime("%Y-%m-%d")

        chat_id = update.message.chat.id

        #amount = int(context.args[0])  # 假設用户提供金额作為参數
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

        #cursor.execute('SELECT SUM(amount) FROM transactions WHERE action="fee" AND chat_id = ? AND date BETWEEN ? AND ?', (chat_id, current_month_start, current_month_end))
        #add_total = cursor.fetchone()[0] or 0

        cursor.execute('SELECT SUM(amount) FROM transactions WHERE action="fee" AND chat_id = ? AND date BETWEEN ? AND ?', (chat_id, current_month_start, current_month_end))
        fee_total = cursor.fetchone()[0] or 0

        cursor.execute('SELECT SUM(amount) FROM transactions WHERE action="count" AND chat_id = ? AND date BETWEEN ? AND ?', (chat_id, current_month_start, current_month_end))
        last_month_count = cursor.fetchone()[0] or 0

        cursor.execute('SELECT SUM(amount) FROM transactions WHERE action="lock" AND chat_id = ?', (chat_id,))
        lock_total = cursor.fetchone()[0] or 0


        total = add_total - subtract_total - fee_total + last_month_count - lock_total
        context.bot.send_message(chat_id=chat_id, text=f"({new_record_id}) {currentDate} {currentTime} \n手續費:{amount} \n\n------------------------------------------------\n本日:\n入{add_today_count}筆:{add_today_total},出{subtract_today_count}筆:{subtract_today_total}\n本月:\n入{add_count}筆:{add_total},出{subtract_count}筆:{subtract_total}\n手續費月計:{fee_total}\n風控:{lock_total}\n前期結餘:{last_month_count}\n總計:{total}\n(月計-月計手續費+前期結餘)")
        return START


#計算總額
def calculate_balance(update: Update, context: CallbackContext, date_str) -> int:
    chat_id = update.message.chat.id
    # 解析命令参數以獲取年份和月份
    #command_args = context.args
    #if len(command_args) != 1:
    #    context.bot.send_message(chat_id=chat_id, text="請提供正確的日期格式，例如：20xx-8")
    #    return START

    #date_str = command_args[0]
    if date_str.endswith("record"):
        date_str_without_record = date_str[:-len("record")]
        match = re.match(r'(\d{4})-(\d{1,2})', date_str_without_record)
        if not match:
            context.bot.send_message(chat_id=chat_id, text="日期格式不正確，請使用20xx-8或類似格式")
            return START

        year = int(match.group(1))
        month = int(match.group(2))
        # 計算指定月份的開始和结束日期
        start_date = date(year, month, 1)
        end_date = date(year, month, calendar.monthrange(year, month)[1])
        start_date_formatted = start_date.strftime("%Y-%m").zfill(7)
        # 查詢指定月份的入金總額
        cursor.execute('SELECT SUM(amount) FROM transactions WHERE action="add" AND chat_id = ? AND date BETWEEN ? AND ?', (chat_id, start_date, end_date))
        add_total = cursor.fetchone()[0] or 0

        # 查詢指定月份的出金總額
        cursor.execute('SELECT SUM(amount) FROM transactions WHERE action="subtract" AND chat_id = ? AND date BETWEEN ? AND ?', (chat_id, start_date, end_date))
        subtract_total = cursor.fetchone()[0] or 0

        # 查詢指定月份的手續費總額
        cursor.execute('SELECT SUM(amount) FROM transactions WHERE action="fee" AND chat_id = ? AND date BETWEEN ? AND ?', (chat_id, start_date, end_date))
        fee_total = cursor.fetchone()[0] or 0

        previous_month = start_date - timedelta(days=1)
        previous_month_formatted = previous_month.strftime("%Y-%m").zfill(7)
        #previous_month_start = datetime(previous_month.year, previous_month.month, 1)
        #previous_month_end = datetime(previous_month.year, previous_month.month, calendar.monthrange(previous_month.year, previous_month.month)[1])

        cursor.execute('SELECT SUM(amount) FROM transactions WHERE action="count" AND chat_id = ? AND date BETWEEN ? AND ?', (chat_id, start_date, end_date))
        last_month_count = cursor.fetchone()[0] or 0


        cursor.execute('SELECT COUNT(*) FROM transactions WHERE (action="add" OR action="subtract") AND chat_id = ? AND date BETWEEN ? AND ?', (chat_id, start_date, end_date))
        transaction_count = cursor.fetchone()[0] or 0

        # 計算結算
        total_month = add_total - subtract_total
        balance = add_total - subtract_total - fee_total + last_month_count
        now = datetime.now()
        currentDate = now.strftime("%Y-%m-%d")
        currentTime = now.strftime("%H:%M:%S")
        #current_month_start = datetime(now.year, now.month, 1)
        #current_month_end = datetime(now.year, now.month, calendar.monthrange(now.year, now.month)[1])

        cursor.execute('INSERT INTO transactions (chat_id, action, amount, date, time, note) VALUES (?, ?, ?, ?, ?, ?)', (chat_id, "count", balance, currentDate, currentTime, "上月結算"))
        conn.commit()
        context.bot.send_message(chat_id=chat_id, text=f"{previous_month_formatted} 結餘：{last_month_count}\n{start_date_formatted} 共{transaction_count}筆資料,總計:{total_month}\n{start_date_formatted} 手續費:{fee_total}\n{start_date_formatted} 月計- 月計手續費+前期結餘,總結算:{balance}\n成功新增到月底結餘")

    else:
        # 如果參數不包含 "record"，執行默認的邏輯並將數據寫入數據庫
        # 解析年份和月份
        match = re.match(r'(\d{4})-(\d{1,2})', date_str)
        if not match:
            context.bot.send_message(chat_id=chat_id, text="日期格式不正確，請使用20xx-8或類似格式")
            return START

        year = int(match.group(1))
        month = int(match.group(2))
        # 計算指定月份的開始和结束日期
        start_date = date(year, month, 1)
        end_date = date(year, month, calendar.monthrange(year, month)[1])
        start_date_formatted = start_date.strftime("%Y-%m").zfill(7)

        # 查詢指定月份的入金總額
        cursor.execute('SELECT SUM(amount) FROM transactions WHERE action="add" AND chat_id = ? AND date BETWEEN ? AND ?', (chat_id, start_date, end_date))
        add_total = cursor.fetchone()[0] or 0

        # 查詢指定月份的出金總額
        cursor.execute('SELECT SUM(amount) FROM transactions WHERE action="subtract" AND chat_id = ? AND date BETWEEN ? AND ?', (chat_id, start_date, end_date))
        subtract_total = cursor.fetchone()[0] or 0

        # 查詢指定月份的手續費總額
        cursor.execute('SELECT SUM(amount) FROM transactions WHERE action="fee" AND chat_id = ? AND date BETWEEN ? AND ?', (chat_id, start_date, end_date))
        fee_total = cursor.fetchone()[0] or 0

        previous_month = start_date - timedelta(days=1)
        previous_month_formatted = previous_month.strftime("%Y-%m").zfill(7)

        #previous_month_start = datetime(previous_month.year, previous_month.month, 1)
        #previous_month_end = datetime(previous_month.year, previous_month.month, calendar.monthrange(previous_month.year, previous_month.month)[1])

        now = datetime.now()
        currentDate = now.strftime("%Y-%m-%d")
        currentTime = now.strftime("%H:%M:%S")
        #current_month_start = datetime(now.year, now.month, 1)
        #current_month_end = datetime(now.year, now.month, calendar.monthrange(now.year, now.month)[1])
        cursor.execute('SELECT SUM(amount) FROM transactions WHERE action="count" AND chat_id = ? AND date BETWEEN ? AND ?', (chat_id, start_date, end_date))
        last_month_count = cursor.fetchone()[0] or 0

        cursor.execute('SELECT COUNT(*) FROM transactions WHERE (action="add" OR action="subtract") AND chat_id = ? AND date BETWEEN ? AND ?', (chat_id, start_date, end_date))
        transaction_count = cursor.fetchone()[0] or 0

        cursor.execute('SELECT SUM(amount) FROM transactions WHERE action="lock" AND chat_id = ?', (chat_id,))
        lock_total = cursor.fetchone()[0] or 0

        # 計算结算
        total_month = add_total - subtract_total
        balance = add_total - subtract_total - fee_total + last_month_count

        context.bot.send_message(chat_id=chat_id, text=f"{previous_month_formatted} 結餘：{last_month_count}\n{start_date_formatted} 共{transaction_count}筆資料,總計:{total_month}\n{start_date_formatted} 手續費:{fee_total}\n{start_date_formatted} 月計-月計手續費+前期結餘-風控,總結算:{balance}")
    return START

def delete_records(update: Update, context: CallbackContext, id_to_delete, date_to_delete) -> int:
    chat_id = update.message.chat.id

    # 解析命令参數以獲取ID和日期
    #command_args = context.args
    #if len(command_args) != 2:
    #    context.bot.send_message(chat_id=chat_id, text="請提供正確的命令格式，例如：/del id 20xx-9-xx")
    #    return START

    #id_to_delete = command_args[0]
    #date_to_delete = command_args[1]

    # 驗證日期格式
    try:
        datetime.strptime(date_to_delete, "%Y-%m-%d")
    except ValueError:
        context.bot.send_message(chat_id=chat_id, text="日期格式不正確，請使用正確的日期格式，例如：20xx-9-xx")
        return START

    # 删除指定ID和日期的數據紀錄以及與该ID和日期相關的所有數據紀錄
    cursor.execute('DELETE FROM transactions WHERE id = ? AND date = ? AND chat_id = ?', (id_to_delete, date_to_delete, chat_id))
    conn.commit()

    context.bot.send_message(chat_id=chat_id, text=f"已删除ID為 {id_to_delete}，日期為 {date_to_delete} 的數據紀錄以及相關的所有數據紀錄")
    return START


# 新的命令处理器，用于列出指定日期的 (ID) 时间 金额 数据
def list_records(update: Update, context: CallbackContext, date_to_list) -> int:
    chat_id = update.message.chat.id

    # 解析命令参数以获取日期
    #command_args = context.args
    #if len(command_args) != 1:
    #    context.bot.send_message(chat_id=chat_id, text="請提供正確的命令格式，例如：/list 20xx-xx 或 /list 20xx-xx-xx")
    #    return START

    #date_to_list = command_args[0]

    # 验证日期格式
    if re.match(r'\d{4}-\d{2}-\d{2}', date_to_list):
        # 如果日期格式为 20xx-xx-xx，列出指定日期的记录
        cursor.execute('SELECT id, date, time, amount, note FROM transactions WHERE date = ? AND chat_id = ?', (date_to_list, chat_id))
        records = cursor.fetchall()

        if not records:
            context.bot.send_message(chat_id=chat_id, text=f"没有找到{date_to_list}的紀錄")
        else:
            response_text = f"{date_to_list} 的紀錄：\n"
            for record in records:
              #  action_symbol = "+" if record[2] == #"add" else "-"  # 根据交易类型添加正负符号
                response_text += f"({record[0]}) {record[1]} {record[2]} \n {record[4]} {record[3]}\n"
            context.bot.send_message(chat_id=chat_id, text=response_text)
    elif re.match(r'\d{4}-\d{2}', date_to_list):
        # 如果日期格式为 20xx-xx，列出指定月份的记录
        cursor.execute('SELECT id, date, time, amount, note FROM transactions WHERE date LIKE ? AND chat_id = ?', (f'{date_to_list}%', chat_id))
        records = cursor.fetchall()

        if not records:
            context.bot.send_message(chat_id=chat_id, text=f"没有找到{date_to_list}的紀錄")
        else:
            response_text = f"{date_to_list} 的紀錄：\n"
            for record in records:
               # action_symbol = "+" if record[1] == #"add" else "-"  # 根据交易类型添加正负符号
                response_text += f"({record[0]}) {record[1]} {record[2]} \n {record[4]} {record[3]}\n"
            context.bot.send_message(chat_id=chat_id, text=response_text)
    else:
        context.bot.send_message(chat_id=chat_id, text="日期格式不正確，请使用正確的日期格式，例如：20xx-xx 或 20xx-xx-xx")

    return START


    # 查询指定日期的 (ID) 时间 金额 数据
    cursor.execute('SELECT id, date, time, amount, note FROM transactions WHERE date = ? AND chat_id = ?', (date_to_list, chat_id))
    records = cursor.fetchall()

    if not records:
        context.bot.send_message(chat_id=chat_id, text=f"没有找到 {date_to_list} 的紀錄")
    else:
        response_text = f"{date_to_list} 的紀錄：\n"
        for record in records:
            #action_symbol = "+" if record[3] == "add" else "-"  # 根据交易类型添加正负符号
            response_text += f"({record[0]}) {record[1]} {record[2]} \n {record[4]} {record[3]}\n"
        context.bot.send_message(chat_id=chat_id, text=f"{response_text}")
        #update.message.reply_text(response_text)

    return START

def export_to_excel(update: Update, context: CallbackContext, date_str) -> int:
    chat_id = update.message.chat.id
    # 解析命令参数以获取年份和月份
    #command_args = context.args
    #if len(command_args) != 1:
    #    context.bot.send_message(chat_id=chat_id, text="请提供正确的日期格式，例如：20xx-xx")
    #    return START

    #date_str = command_args[0]

    # 验证日期格式
    if not re.match(r'\d{4}-\d{2}', date_str):
        context.bot.send_message(chat_id=chat_id, text="日期格式不正确，请使用20xx-xx的格式")
        return START

    chat_title = update.message.chat.title
    year_month = date_str
    file_name = f" {chat_title}-{year_month}.xlsx"  # 替换群组名稱为实际的群组名

    # 查询指定月份的数据
    cursor.execute('SELECT date, time, action, amount FROM transactions WHERE date LIKE ? AND chat_id = ?', (f'{year_month}%', chat_id))
    data = cursor.fetchall()

    if not data:
        context.bot.send_message(chat_id=chat_id, text=f"没有找到{year_month}的数据记录")
        return START

    # 创建一个DataFrame来存储数据
    df = pd.DataFrame(data, columns=['日期', '時間', '類別', '金额'])

    # 将数据保存为Excel文件
    df.to_excel(file_name, index=False)

    # 发送Excel文件给用户
    with open(file_name, 'rb') as excel_file:
        context.bot.send_document(chat_id=chat_id, document=excel_file)

    return START

#顯示目前狀

def show(update: Update, context: CallbackContext) -> int:
        chat_id = update.message.chat.id

        now = datetime.now()


        currentDate = now.strftime("%Y-%m-%d")
        currentTime = now.strftime("%H:%M:%S")

        current_month_start = date(now.year, now.month, 1)

        current_month_end = date(now.year, now.month, calendar.monthrange(now.year, now.month)[1])

        today = date.today().strftime("%Y-%m-%d")
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

        cursor.execute('SELECT SUM(amount) FROM transactions WHERE action="lock" AND chat_id = ?', (chat_id,))
        lock_total = cursor.fetchone()[0] or 0


        total = add_total - subtract_total - fee_total + last_month_count - lock_total

        context.bot.send_message(chat_id=chat_id, text=f"{currentDate} {currentTime} \n\n\n------------------------------------------------\n本日:\n入{add_today_count}筆:{add_today_total},出{subtract_today_count}筆:{subtract_today_total}\n本月:\n入{add_count}筆:{add_total},出{subtract_count}筆:{subtract_total}\n手續費月計:{fee_total}\n風控:{lock_total}\n前期結餘:{last_month_count}\n總計:{total}\n(月計-月計手續費+前期結餘)")
        return START


def list_daily_flow(update: Update, context: CallbackContext, date_to_list) -> int:
    chat_id = update.message.chat.id

    # 解析命令参数以获取日期
    #command_args = context.args
    #if len(command_args) != 1:
    #    context.bot.send_message(chat_id=chat_id, text="請提供正確的命令格式，例如：/flow 20xx-xx")
    #    return START

    #date_to_list = command_args[0]

    # 验证日期格式
    if not re.match(r'\d{4}-\d{2}', date_to_list):
        context.bot.send_message(chat_id=chat_id, text="日期格式不正確，請使用正確的日期格式，例如：20xx-xx")
        return START

    # 查询指定月份每日入金量
    cursor.execute('SELECT date, SUM(amount) FROM transactions WHERE action="add" AND date LIKE ? AND chat_id = ? GROUP BY date', (f'{date_to_list}%', chat_id))
    daily_flows = cursor.fetchall()

    if not daily_flows:
        context.bot.send_message(chat_id=chat_id, text=f"没有找到{date_to_list}的入金紀錄")
    else:
        response_text = f"{date_to_list} 的每日入金量列表：\n"
        for daily_flow in daily_flows:
            response_text += f"{daily_flow[0]}：{daily_flow[1]} \n"
        context.bot.send_message(chat_id=chat_id, text=response_text)

    return START

def lock(update: Update, context: CallbackContext, amount) -> int:
        now = datetime.now()
        currentDate = now.strftime("%Y-%m-%d")
        currentTime = now.strftime("%H:%M:%S")
        current_month_start = date(now.year, now.month, 1)
        current_month_end = date(now.year, now.month, calendar.monthrange(now.year, now.month)[1])
        today = date.today().strftime("%Y-%m-%d")

        chat_id = update.message.chat.id

        #amount = int(context.args[0])
        cursor.execute('INSERT INTO transactions (chat_id, action, amount, date, time, note) VALUES (?, ?, ?, ?, ?, ?)', (chat_id, "lock", amount, currentDate, currentTime, "風控"))
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

        cursor.execute('SELECT SUM(amount) FROM transactions WHERE action="lock" AND chat_id = ?', (chat_id,))
        lock_total = cursor.fetchone()[0] or 0


        total = add_total - subtract_total - fee_total + last_month_count - lock_total
        context.bot.send_message(chat_id=chat_id, text=f"({new_record_id}) {currentDate} {currentTime} \n風控{amount} \n\n------------------------------------------------\n本日:\n入{add_today_count}筆:{add_today_total},出{subtract_today_count}筆:{subtract_today_total}\n本月:\n入{add_count}筆:{add_total},出{subtract_count}筆:{subtract_total}\n手續費月計:{fee_total}\n風控:{lock_total}\n前期結餘:{last_month_count}\n總計:{total}\n(月計-月計手續費+前期結餘)")
        return START

def handle_custom_command(update, context):
    # 获取消息文本
    message_text = update.message.text
    command_args = message_text.split()
    # 检查消息是否以 '/+ 数字' 格式开头
    if message_text.startswith('/+ '):
        try:
            # 提取数字部分并转换为整数
            number = float(message_text[3:])
            # 调用 add 函数并传递数字作为参数
            add(update, context, number)
        except ValueError:
            # 如果提取的部分不是有效的数字，可以进行错误处理
            update.message.reply_text("/+ 數字")
    elif message_text.startswith('/- '):
        try:
            # 提取数字部分并转换为整数
            number = float(message_text[3:])
            # 调用 add 函数并传递数字作为参数
            subtract(update, context, number)
        except ValueError:
            # 如果提取的部分不是有效的数字，可以进行错误处理
            update.message.reply_text("/- 數字")
    elif message_text.startswith('/手續費 ') or message_text.startswith('/手续费 '):
        try:
            # 提取数字部分并转换为整数
            number = float(message_text[5:])
            # 调用 add 函数并传递数字作为参数
            add_fee(update, context, number)
        except ValueError:
            # 如果提取的部分不是有效的数字，可以进行错误处理
            update.message.reply_text("/手續費 數字")
    elif message_text.startswith('/刪除 ') or message_text.startswith('/删除 '):
        try:
            # 提取数字部分并转换为整数
            id_to_delete = command_args[1]
            date_to_delete = command_args[2]
            # 调用 add 函数并传递数字作为参数
            delete_records(update, context, id_to_delete, date_to_delete)
        except ValueError:
            # 如果提取的部分不是有效的数字，可以进行错误处理
            update.message.reply_text("/刪除 編號 日期(/刪除30 2023-01-01)")
    elif message_text.startswith('/風控 ') or message_text.startswith('/风控 '):
        try:
            # 提取数字部分并转换为整数
            number = float(message_text[4:])
            # 调用 add 函数并传递数字作为参数
            lock(update, context, number)
        except ValueError:
            # 如果提取的部分不是有效的数字，可以进行错误处理
            update.message.reply_text("/風控 數字")
    elif message_text.startswith('/流量 ') or message_text.startswith('/流量 '):
        try:
            # 提取数字部分并转换为整数
            date_for_flow = command_args[1]
            # 调用 add 函数并传递数字作为参数
            list_daily_flow(update, context, date_for_flow)
        except ValueError:
            # 如果提取的部分不是有效的数字，可以进行错误处理
            update.message.reply_text("/流量  日期(/流量 2023-01-01 or 2023-01)")
    elif message_text.startswith('/列表 ') or message_text.startswith('/列表 '):
        try:
            # 提取数字部分并转换为整数
            date_to_list = command_args[1]
            # 调用 add 函数并传递数字作为参数
            list_records(update, context, date_to_list)
        except ValueError:
            # 如果提取的部分不是有效的数字，可以进行错误处理
            update.message.reply_text("/列表  日期(/列表 2023-01-01 or 2023-01)")
    elif message_text.startswith('/匯出 ') or message_text.startswith('/汇出 '):
        try:
            # 提取数字部分并转换为整数
            date_to_export = command_args[1]
            # 调用 add 函数并传递数字作为参数
            export_to_excel(update, context, date_to_export)
        except ValueError:
            # 如果提取的部分不是有效的数字，可以进行错误处理
            update.message.reply_text("/匯出  日期(/匯出 2023-01-01 or 2023-01)")
    elif message_text.startswith('/結算 ') or message_text.startswith('/结算 '):
        try:
            # 提取数字部分并转换为整数
            monuth_to_count = command_args[1]
            # 调用 add 函数并传递数字作为参数
            calculate_balance(update, context, monuth_to_count)
        except ValueError:
            # 如果提取的部分不是有效的数字，可以进行错误处理
            update.message.reply_text("/結算  日期(/結算 2023-01 or /結算 2023-01record )")
    elif message_text.startswith('/顯示')or message_text.startswith('/显示'):
        #try:
            # 调用 add 函数并传递数字作为参数
            show(update, context)
        #except ValueError:
            # 如果提取的部分不是有效的数字，可以进行错误处理
            #update.message.reply_text("/顯示")


# 在main函数中添加新的命令处理器

# 創建機器人處理程序
def main() -> None:
    updater = Updater(token='6595335812:AAHMPUFAKw6I3FHeSTX6bHL0QPST79CXB3U', use_context=True)
    dispatcher = updater.dispatcher

    updater.dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_custom_command))
    dispatcher.add_handler(CommandHandler('help', start))
    #dispatcher.add_handler(CommandHandler('a', add, pass_args=True))
    #dispatcher.add_handler(CommandHandler('b', subtract, pass_args=True))
    #dispatcher.add_handler(CommandHandler('fee', add_fee, pass_args=True))
    #dispatcher.add_handler(CommandHandler('del', delete_records, pass_args=True))
    #dispatcher.add_handler(CommandHandler('count', calculate_balance, pass_args=True))
    #dispatcher.add_handler(CommandHandler('list', list_records, pass_args=True))
    #dispatcher.add_handler(CommandHandler('export', export_to_excel, pass_args=True))
    #dispatcher.add_handler(CommandHandler('show', show))
    #dispatcher.add_handler(CommandHandler('flow', list_daily_flow, pass_args=True))
    #dispatcher.add_handler(CommandHandler('lock', lock, pass_args=True))
    #dispatcher.add_handler(CommandHandler('handle', handle_custom_command))
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
