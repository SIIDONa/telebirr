import os
import asyncio
import threading
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
)

from database import init_db, exists, save
from verifier import verify

# ======================
# CONFIGURATION
# ======================
TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

# ያንተን የቴሌብር መረጃ እዚህ አስተካክል (ቦቱ ገንዘቡ ለአንተ መግባቱን የሚያረጋግጥበት)
MY_RECEIVER_NAME = "Melaku Abraham Ersedo"
MY_RECEIVER_PHONE = "2519XXXX4952" 

app = Flask(__name__)
telegram_app = Application.builder().token(TOKEN).build()

# ======================
# COMMANDS
# ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    buttons = [
        [InlineKeyboardButton("🧾 Verify Receipt", callback_data="verify")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="help")]
    ]
    await update.message.reply_text(
        "👋 ሰላም! እኔ Telebirr Receipt Verification Bot ነኝ።\n"
        "የቴሌብር ክፍያ Receipt Number ወይም SMS Receipt Link ላክልኝ እና አረጋግጥልሃለሁ።",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ መረጃ\n"
        "1) Receipt Number ይላኩ (ምሳሌ: DGH9WN4E4H)\n"
        "2) ወይም የ SMS ሊንኩን ሙሉውን ይላኩ"
    )

# ======================
# BUTTON HANDLER
# ======================
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "verify":
        await query.message.reply_text("🧾 እባክዎ Receipt Number ወይም Link ላክ።")
    elif query.data == "help":
        await query.message.reply_text("የከፈሉበትን ሪሲፕት ቁጥር ይላኩ እና እመርምረዋለሁ።")

# ======================
# RECEIPT CHECK
# ======================
async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    status_msg = await update.message.reply_text("🔍 ሪሲፕቱን እያጣራሁ ነው...")
    
    # ሪሲፕቱን ከቴሌኮም ማጣራት
    result = verify(text, expected_receiver_name=MY_RECEIVER_NAME, expected_receiver_no=MY_RECEIVER_PHONE)
    
    if not result["ok"]:
        if result.get("transient"):
            await status_msg.edit_text("⚠️ የቴሌብር ሲስተም በአሁኑ ሰአት አይሰራም (Busy)። እባክዎ ትንሽ ቆይተው ይሞክሩ።")
        else:
            await status_msg.edit_text(f"❌ {result['error']}")
        return

    if not result["verified"]:
        await status_msg.edit_text(
            f"❌ ማረጋገጥ አልተቻለም!\n"
            f"ምክንያት፡ የተቀባዩ ስም/አካውንት አይመሳሰልም፣ ወይም ክፍያው አልተጠናቀቀም (Status: {result.get('status', 'Unknown')})።"
        )
        return

    receipt_id = result["transactionId"]
    
    # ዳታቤዝ ላይ መኖሩን (Deduplication) ማረጋገጥ
    if exists(receipt_id):
        await status_msg.edit_text(f"⚠️ ይህ ሪሲፕት ({receipt_id}) ከዚህ በፊት ጥቅም ላይ ውሏል!")
        return
        
    # ዳታቤዝ ላይ ሴቭ ማድረግ
    save(result)
    
    await status_msg.edit_text(
        f"✅ ክፍያዎ ተረጋግጧል!\n\n"
        f"🧾 ሪሲፕት: {receipt_id}\n"
        f"👤 የላኪ ስም: {result['payerName']}\n"
        f"💰 መጠን: {result['amountText']}\n"
        f"📅 ቀን: {result['paymentDate']}\n"
        f"📌 Status: SUCCESS"
    )

# ======================
# REGISTER HANDLERS
# ======================
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("help", help_command))
telegram_app.add_handler(CallbackQueryHandler(button))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check))


# ======================
# WORKER-SAFE BACKGROUND LOOP
# ======================
worker_loop = None
bot_initialized = False
lock = threading.Lock()

def start_background_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

def init_bot():
    global worker_loop, bot_initialized
    with lock:
        if bot_initialized:
            return
        worker_loop = asyncio.new_event_loop()
        threading.Thread(target=start_background_loop, args=(worker_loop,), daemon=True).start()
        
        async def setup():
            init_db()
            await telegram_app.initialize()
            await telegram_app.start()
            if WEBHOOK_URL:
                await telegram_app.bot.set_webhook(f"{WEBHOOK_URL.rstrip('/')}/webhook")
                
        asyncio.run_coroutine_threadsafe(setup(), worker_loop)
        bot_initialized = True

# ======================
# FLASK WEBHOOK ROUTES
# ======================
@app.route("/")
def home():
    init_bot()
    return "Telebirr Verification Bot is Running Successfully!"

@app.route("/webhook", methods=["POST"])
def webhook():
    init_bot()
    data = request.get_json(force=True)
    if data:
        update = Update.de_json(data, telegram_app.bot)
        if worker_loop:
            asyncio.run_coroutine_threadsafe(telegram_app.process_update(update), worker_loop)
    return "ok", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
