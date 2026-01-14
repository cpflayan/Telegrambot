import re, calendar, pandas as pd
from datetime import datetime, date, timedelta
from telegram import Update
from telegram.ext import CallbackContext
from database import get_conn, get_summary_report

def start(update: Update, context: CallbackContext):
    menu = ("/+  數字\n/-  數字\n/手續費  數字\n/刪除  編號  日期\n/風控  數字\n"
            "/顯示\n/流量  2023-01\n/列表  2023-01\n/匯出  2023-01\n/結算  2023-01")
    update.message.reply_text(menu)

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
    conn = get_conn(); cursor = conn.cursor()
    cursor.execute('DELETE FROM transactions WHERE id = ? AND date = ? AND chat_id = ?', (id_to_delete, date_to_delete, chat_id))
    conn.commit(); conn.close()
    update.message.reply_text(f"已刪除 ID:{id_to_delete} 日期:{date_to_delete}")

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
    is_record = "record" in date_str
    clean_date = date_str.replace("record", "")
    try:
        year, month = map(int, clean_date.split('-'))
        start_date = date(year, month, 1)
        end_date = date(year, month, calendar.monthrange(year, month)[1])
    except:
        update.message.reply_text("格式錯誤，範例: 2023-01")
        return

    conn = get_conn(); cursor = conn.cursor()
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
    
    if is_record:
        now = datetime.now()
        cursor.execute('INSERT INTO transactions (chat_id, action, amount, date, time, note) VALUES (?, ?, ?, ?, ?, ?)', 
                       (chat_id, "count", balance, now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"), "上月結算"))
        conn.commit()
        msg = f"{clean_date} 結算並存入資料庫成功\n"
    else:
        msg = f"{clean_date} 預覽結算\n"
        
    conn.close()
    msg += f"共 {count} 筆, 總結算: {balance}"
    update.message.reply_text(msg)
