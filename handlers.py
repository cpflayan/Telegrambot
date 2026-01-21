import re, calendar, pandas as pd
from datetime import datetime, date, timedelta
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton,InlineKeyboardButton, InlineKeyboardMarkup, ForceReply
from telegram.ext import CallbackContext
from database import get_conn, get_summary_report

# 定義常駐選單，方便各個函數調用
main_menu_markup = ReplyKeyboardMarkup(
    [['💰 入金 (+)', '💸 出金 (-)', '📊 顯示統計'], ['🪙 手續費', '🚨 風控', '❌ 刪除'],['🔢 結算預覽', '⌨️ 結算計入', '❓ 幫助']],
    resize_keyboard=True,
    one_time_keyboard=False,
    is_persistent=True# 確保不會點完就消失
)

def start(update: Update, context: CallbackContext):
    menu = ("指令使用方式    \n/+  數字\n/-  數字\n/手續費  數字\n/刪除  編號  日期\n/風控  數字\n"
            "/顯示\n/流量  2023-01\n/列表  2023-01\n/匯出  2023-01\n/結算  2023-01（預覽）\n/結算計入  2023-01（寫入）")
    update.message.reply_text(menu)

    resize_keyboard=True #讓按鈕高度不要太大
    persistent=True #(2026年新版支援) 讓選單更穩定顯示
    update.message.reply_text(
        '💾 版本v1.6.0升級公告：\n1.結算功能優化,指令：/結算 改為預覽不寫入、新增指令：/結算計入 結算並寫入紀錄。\n2.新增按鈕功能，互動式操作更方便。'
        )
    update.message.reply_text(
        '🏦 記帳系統：選單已開啟。\n您可以點擊下方按鈕或直接輸入指令。', 
        reply_markup=main_menu_markup
    )

def record_transaction(chat_id, action, amount, note):
    conn = get_conn()
    cursor = conn.cursor()
    now = datetime.now()
    cur_date, cur_time = now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S")
    cursor.execute('INSERT INTO transactions (chat_id, action, amount, date, time, note) VALUES (?, ?, ?, ?, ?, ?)', 
                   (chat_id, action, amount, cur_date, cur_time, note))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id, cur_date, cur_time

def add(update, context, amount):
    chat_id = update.message.chat.id
    new_id, d, t = record_transaction(chat_id, "add", amount, "入")
    update.message.reply_text(f"({new_id}) {d} {t} \n+{amount}\n\n{'-'*30}\n{get_summary_report(chat_id)}")

def subtract(update, context, amount):
    chat_id = update.message.chat.id
    new_id, d, t = record_transaction(chat_id, "subtract", amount, "出")
    update.message.reply_text(f"({new_id}) {d} {t} \n-{amount}\n\n{'-'*30}\n{get_summary_report(chat_id)}")

def add_fee(update, context, amount):
    chat_id = update.message.chat.id
    new_id, d, t = record_transaction(chat_id, "fee", amount, "手續費")
    update.message.reply_text(f"({new_id}) {d} {t} \n手續費:{amount}\n\n{'-'*30}\n{get_summary_report(chat_id)}")

def lock(update, context, amount):
    chat_id = update.message.chat.id
    new_id, d, t = record_transaction(chat_id, "lock", amount, "風控")
    update.message.reply_text(f"({new_id}) {d} {t} \n風控:{amount}\n\n{'-'*30}\n{get_summary_report(chat_id)}")

def show(update, context):
    chat_id = update.message.chat.id
    now = datetime.now()
    update.message.reply_text(f"{now.strftime('%Y-%m-%d %H:%M:%S')}\n\n{'-'*30}\n{get_summary_report(chat_id)}")

def delete_records(update, context, id_to_delete, date_to_delete):
    chat_id = update.message.chat.id
    conn = get_conn() 
    cursor = conn.cursor()
    cursor.execute('DELETE FROM transactions WHERE id = ? AND date = ? AND chat_id = ?', (id_to_delete, date_to_delete, chat_id))
    if cursor.rowcount > 0:
        msg = f"✅ 已成功刪除 ID:{id_to_delete} (日期:{date_to_delete})"
    else:
        msg = f"❌ 找不到對應紀錄 (ID:{id_to_delete}, 日期:{date_to_delete})"
    conn.commit()
    conn.close()
    # 刪除完後，記得帶回常駐選單！
    update.message.reply_text(msg)

def list_records(update, context, date_str):
    chat_id = update.message.chat.id
    conn = get_conn(); cursor = conn.cursor()
    if len(date_str) == 7: # 2023-01
        cursor.execute('SELECT id, date, time, amount, note FROM transactions WHERE date LIKE ? AND chat_id = ?', (f'{date_str}%', chat_id))
    else: # 2023-01-01
        cursor.execute('SELECT id, date, time, amount, note FROM transactions WHERE date = ? AND chat_id = ?', (date_str, chat_id))
    records = cursor.fetchall()
    conn.close()
    if not records:
        update.message.reply_text("查無資料")
        return
    res = f"{date_str} 紀錄：\n" + "".join([f"({r[0]}) {r[1]} {r[2]}\n{r[4]} {r[3]}\n" for r in records])
    update.message.reply_text(res)

def export_to_excel(update, context, date_str):
    chat_id = update.message.chat.id
    conn = get_conn(); cursor = conn.cursor()
    cursor.execute('SELECT date, time, action, amount FROM transactions WHERE date LIKE ? AND chat_id = ?', (f'{date_str}%', chat_id))
    data = cursor.fetchall()
    conn.close()
    if not data:
        update.message.reply_text("查無資料")
        return
    df = pd.DataFrame(data, columns=['日期', '時間', '類別', '金額'])
    file_name = f"Report-{date_str}.xlsx"
    df.to_excel(file_name, index=False)
    with open(file_name, 'rb') as f:
        context.bot.send_document(chat_id=chat_id, document=f)
    update.message.reply_text(res)


def list_daily_flow(update, context, date_str):
    chat_id = update.message.chat.id
    conn = get_conn(); cursor = conn.cursor()
    cursor.execute('SELECT date, SUM(amount) FROM transactions WHERE action="add" AND date LIKE ? AND chat_id = ? GROUP BY date', (f'{date_str}%', chat_id))
    flows = cursor.fetchall()
    conn.close()
    if not flows:
        update.message.reply_text("查無入金紀錄")
        return
    res = f"{date_str} 每日入金：\n" + "".join([f"{f[0]}：{f[1]}\n" for f in flows])
    update.message.reply_text(res)

def calculate_balance(update, context, date_str):
    chat_id = update.message.chat.id
    try:
        year, month = map(int, date_str.split('-'))
        start_date = date(year, month, 1)
        end_date = date(year, month, calendar.monthrange(year, month)[1])
    except:
        update.message.reply_text("格式錯誤，範例: 2023-01")
        return

    conn = get_conn()
    cursor = conn.cursor()
    def q(sql):
        cursor.execute(sql, (chat_id, start_date, end_date))
        res = cursor.fetchone()
        return res[0] if res and res[0] is not None else 0

    add_t = q('SELECT SUM(amount) FROM transactions WHERE action="add" AND chat_id=? AND date BETWEEN ? AND ?')
    sub_t = q('SELECT SUM(amount) FROM transactions WHERE action="subtract" AND chat_id=? AND date BETWEEN ? AND ?')
    fee_t = q('SELECT SUM(amount) FROM transactions WHERE action="fee" AND chat_id=? AND date BETWEEN ? AND ?')
    last_t = q('SELECT SUM(amount) FROM transactions WHERE action="count" AND chat_id=? AND date BETWEEN ? AND ?')
    count = q('SELECT COUNT(*) FROM transactions WHERE (action="add" OR action="subtract") AND chat_id=? AND date BETWEEN ? AND ?')
    
    balance = add_t - sub_t - fee_t + last_t
    msg = f"{date_str} 預覽結算\n"    
    conn.close()
    msg = f"✅ {date_str} 結算預覽\n"
    msg += f"------------------------------\n"
    msg += f"📥 入金總計：{add_t}\n"
    msg += f"📤 出金總計：{sub_t}\n"
    msg += f"🧧 手續費總計：{fee_t}\n"
    msg += f"💰 最終結轉餘額：{balance}\n"
    msg += f"📊 處理單據：{count} 筆"
    update.message.reply_text(msg)

def calculate_balance_write(update, context, date_str):
    chat_id = update.message.chat.id
    try:
        year, month = map(int, date_str.split('-'))
        start_date = date(year, month, 1)
        end_date = date(year, month, calendar.monthrange(year, month)[1])
    except:
        update.message.reply_text("格式錯誤，範例: 2023-01")
        return
    conn = get_conn()
    cursor = conn.cursor()
    # --- 新增：防止重複結算檢查 ---
    # 檢查該 chat_id 在該月份是否已經有 action="count" 的紀錄
    note_search = f"{date_str} 結算"
    cursor.execute(
        'SELECT id FROM transactions WHERE chat_id = ? AND action = "count" AND note = ?',
        (chat_id, note_search)
    )
    if cursor.fetchone():
        conn.close()
        update.message.reply_text(f"⚠️ 警告：{date_str} 已經結算過了，不可重複操作。")
        return
    # ---------------------------
    def q(sql):
        cursor.execute(sql, (chat_id, start_date, end_date))
        res = cursor.fetchone()
        return res[0] if res and res[0] is not None else 0

    add_t = q('SELECT SUM(amount) FROM transactions WHERE action="add" AND chat_id=? AND date BETWEEN ? AND ?')
    sub_t = q('SELECT SUM(amount) FROM transactions WHERE action="subtract" AND chat_id=? AND date BETWEEN ? AND ?')
    fee_t = q('SELECT SUM(amount) FROM transactions WHERE action="fee" AND chat_id=? AND date BETWEEN ? AND ?')
    last_t = q('SELECT SUM(amount) FROM transactions WHERE action="count" AND chat_id=? AND date BETWEEN ? AND ?')
    count = q('SELECT COUNT(*) FROM transactions WHERE (action="add" OR action="subtract") AND chat_id=? AND date BETWEEN ? AND ?')

    balance = add_t - sub_t - fee_t + last_t
    now = datetime.now()
    note_text = f"{date_str} 結算"
    cursor.execute('INSERT INTO transactions (chat_id, action, amount, date, time, note) VALUES (?, ?, ?, ?, ?, ?)',
                       (chat_id, "count", balance, now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"), note_text))
    conn.commit()
    msg = f"{date_str} 結算並存入資料庫成功\n"
    conn.close()
    msg = f"✅ {date_str} 結算成功並已存入資料庫\n"
    msg += f"------------------------------\n"
    msg += f"📥 入金總計：{add_t}\n"
    msg += f"📤 出金總計：{sub_t}\n"
    msg += f"🧧 手續費總計：{fee_t}\n"
    msg += f"💰 最終結轉餘額：{balance}\n"
    msg += f"📊 處理單據：{count} 筆"
    update.message.reply_text(msg)

