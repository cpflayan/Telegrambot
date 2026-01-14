import logging
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from config import BOT_TOKEN, AUTHORIZED_GROUPS
from database import init_db
import handlers

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

def handle_custom_command(update, context):
    if not update.message or not update.message.text: return
    chat_id = update.effective_chat.id
    chat_title = update.effective_chat.title
    # --- 1. 權限檢查開始 ---
    if chat_id not in AUTHORIZED_GROUPS:
        # 在伺服器後台印出 ID，方便管理者獲取正確的群組 ID 填入 config.py
        print(f"⚠️ 拒絕存取 - 群組: {chat_title} (ID: {chat_id})")
        # 如果需要讓使用者知道沒權限，可以取消下行註解
        update.message.reply_text("未獲得授權，請聯繫管理員。")
        return 
    # --- 權限檢查結束 ---
    msg = update.message.text
    args = msg.split()
    
    try:
        if msg.startswith('/+ '): handlers.add(update, context, int(msg[3:]))
        elif msg.startswith('/- '): handlers.subtract(update, context, int(msg[3:]))
        elif msg.startswith(('/手續費 ', '/手续费 ')): handlers.add_fee(update, context, int(args[1]))
        elif msg.startswith(('/風控 ', '/风控 ')): handlers.lock(update, context, int(args[1]))
        elif msg.startswith(('/顯示', '/显示')): handlers.show(update, context)
        elif msg.startswith(('/刪除 ', '/删除 ')): handlers.delete_records(update, context, args[1], args[2])
        elif msg.startswith('/流量 '): handlers.list_daily_flow(update, context, args[1])
        elif msg.startswith('/列表 '): handlers.list_records(update, context, args[1])
        elif msg.startswith(('/匯出 ', '/汇出 ')): handlers.export_to_excel(update, context, args[1])
        elif msg.startswith(('/結算 ', '/结算 ')): handlers.calculate_balance(update, context, args[1])
    except Exception as e:
        update.message.reply_text(f"錯誤: {e}")

def main():
    init_db()
    updater = Updater(token=BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler('start', handlers.start))
    dp.add_handler(CommandHandler('help', handlers.start))
    # 攔截自定義文字指令
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_custom_command))
    # 攔截斜線開頭的指令
    dp.add_handler(MessageHandler(Filters.regex(r'^/'), handle_custom_command))

    print("機器人運行中...")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
