import logging
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram import MenuButtonCommands, ForceReply
from config import BOT_TOKEN, AUTHORIZED_GROUPS
from database import init_db
import handlers

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

def handle_custom_command(update, context):
    if not update.message or not update.message.text: return
    chat_id = update.effective_chat.id
    chat_title = update.effective_chat.title
    msg = update.message.text
    # --- 1. 權限檢查開始 ---
    if chat_id not in AUTHORIZED_GROUPS:
        # 在伺服器後台印出 ID，方便管理者獲取正確的群組 ID 填入 config.py
        print(f"⚠️ 拒絕存取 - 群組: {chat_title} (ID: {chat_id})")
        # 如果需要讓使用者知道沒權限，可以取消下行註解
        update.message.reply_text("未獲得授權，請聯繫管理員。")
        return 
    # --- 權限檢查結束 ---
    # --- 2. 處理狀態下的「純數字」輸入 ---
    # 檢查這個使用者是否正處於「等待輸入金額」的狀態
    current_state = context.user_data.get('state')
    if current_state in ['awaiting_add', 'awaiting_sub', 'awaiting_add_fee', 'awaiting_lock' ]:
        if msg.isdigit(): # 如果使用者輸入的是純數字
            amount = int(msg)
            if current_state == 'awaiting_add':
                handlers.add(update, context, amount)
                context.user_data['state'] = None # 執行完清除狀態
                return
            elif current_state == 'awaiting_sub':
                handlers.subtract(update, context, amount)
                context.user_data['state'] = None
                return
            elif current_state == 'awaiting_add_fee':
                handlers.add_fee(update, context, amount)
                context.user_data['state'] = None
                return
            elif current_state == 'awaiting_lock':
                handlers.lock(update, context, amount)
                context.user_data['state'] = None
                return
            # 如果沒有狀態卻輸入數字，提醒他要先點按鈕或用指令
        else:    
            context.user_data['state'] = None
            update.message.reply_text("請輸入正確數值"
                    #先選擇【入金】或【出金】按鈕，或是使用 /+ 指令。
                    , reply_markup=handlers.main_menu_markup)
            return
    #elif current_state == 'list_button':
        #handlers.show(update, context)
        #context.user_data['state'] = None
        #return
    # --- 第一步：處理 ID 輸入 ---
    elif current_state == 'awaiting_delete_id':
        if msg.isdigit():
            context.user_data['delete_id'] = msg  # 暫存 ID
            context.user_data['state'] = 'awaiting_delete_date' # 切換到下一步
            update.message.reply_text(
                f"✅ 已記錄 ID: {msg}\n請輸入交易日期 (例如: 2026-01-15)：",
                reply_markup=ForceReply(selective=True)
            )
        else:
            update.message.reply_text("❌ ID 必須是數字，請重新輸入：")
        return

    # --- 第二步：處理日期輸入 ---
    elif current_state == 'awaiting_delete_date':
        # 簡單正則檢查日期格式 (YYYY-MM-DD)
        import re
        if re.match(r"^\d{4}-\d{2}-\d{2}$", msg):
            delete_id = context.user_data.get('delete_id')
            handlers.delete_records(update, context, delete_id, msg)

            # 結束後清除所有暫存資訊
            context.user_data['state'] = None
            context.user_data['delete_id'] = None
        else:
            update.message.reply_text("❌ 日期格式錯誤，請輸入 YYYY-MM-DD (例如: 2026-01-15)：")
        return

    #elif current_state == 'help_button':
        #handlers.start(update: Update, context: CallbackContext)
        #context.user_data['state'] = None
        #return
    elif current_state == 'awaiting_settle':
        handlers.calculate_balance(update, context, msg)
        context.user_data['state'] = None
        return

    elif current_state == 'awaiting_settle_write':
        handlers.calculate_balance_write(update, context, msg)
        context.user_data['state'] = None
        return
    
    # --- 啟動按鈕：觸發第一步 ---
    if msg == '❌ 刪除':
        context.user_data['state'] = None
        # 這裡可以噴出一組 Inline 按鈕，或直接問
        update.message.reply_text("【刪除模式】請輸入要刪除的交易 ID：", reply_markup=ForceReply(selective=True))
        context.user_data['state'] = 'awaiting_delete_id'
        return
   
   # --- 處理常駐選單點擊 ---
    elif msg == '💰 入金 (+)':
        context.user_data['state'] = None
        context.user_data['state'] = 'awaiting_add'
        update.message.reply_text(
            "請輸入【入金】金額：",
            reply_markup=ForceReply(selective=True)
        )
        return
    elif msg == '💸 出金 (-)':
        context.user_data['state'] = None
        context.user_data['state'] = 'awaiting_sub'
        update.message.reply_text(
            "請輸入【出金】金額：",
            reply_markup=ForceReply(selective=True)
        )
        return
    elif msg == '📊 顯示統計':
        return handlers.show(update, context)
    elif msg == '❓ 幫助':
        return handlers.start(update, context)
    elif msg == '🪙 手續費':
        context.user_data['state'] = None
        context.user_data['state'] = 'awaiting_add_fee'
        update.message.reply_text(
            "請輸入【手續費】金額：",
            reply_markup=ForceReply(selective=True)
        )
        return
    elif msg == '🚨 風控':
        context.user_data['state'] = None
        context.user_data['state'] = 'awaiting_lock'
        update.message.reply_text(
            "請輸入【風控】金額：",
            reply_markup=ForceReply(selective=True)
        )
        return
    elif msg == '🔢 結算預覽':
        context.user_data['state'] = 'awaiting_settle'
        update.message.reply_text(
            "請輸入【結算】日期：",
            reply_markup=ForceReply(selective=True)
        )
        return
    elif msg == '⌨️ 結算計入':
        context.user_data['state'] = None
        context.user_data['state'] = 'awaiting_settle_write'
        update.message.reply_text(
            "請輸入【結算】日期：",
            reply_markup=ForceReply(selective=True)
        )
        return


    # -----------------------
    
    try:
        # 將訊息按空格拆開，例如 "/刪除 105 2026-01-15" 變成 ["/刪除", "105", "2026-01-15"]
        parts = msg.split()

        if msg.startswith('/+ '): handlers.add(update, context, int(msg[3:]))
        elif msg.startswith('/- '): handlers.subtract(update, context, int(msg[3:]))
        elif msg.startswith(('/手續費 ', '/手续费 ')): handlers.add_fee(update, context, int(parts[1]))
        elif msg.startswith(('/風控 ', '/风控 ')): handlers.lock(update, context, int(parts[1]))
        elif msg.startswith(('/顯示', '/显示')): handlers.show(update, context)
        elif msg.startswith(('/刪除 ', '/删除 ')): handlers.delete_records(update, context, parts[1], parts[2])
        elif msg.startswith('/流量 '): handlers.list_daily_flow(update, context, parts[1])
        elif msg.startswith('/列表 '): handlers.list_records(update, context, parts[1])
        elif msg.startswith(('/匯出 ', '/汇出 ')): handlers.export_to_excel(update, context, parts[1])
        elif msg.startswith(('/結算 ', '/结算 ')): handlers.calculate_balance(update, context, parts[1])
        elif msg.startswith(('/結算計入 ', '/结算计入 ')): handlers.calculate_balance_write(update, context, parts[1])
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
    dp.add_handler(MessageHandler(Filters.status_update.new_chat_members, handlers.start))

    print("機器人運行中...")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
