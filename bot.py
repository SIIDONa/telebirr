import os
import re
import asyncio
import threading
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
)

from database import init_db, exists, save
from verifier import verify

TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

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
        "የTelebirr ክፍያ Receipt Number ወይም SMS Receipt Link ላክልኝ። እኔ አረጋግጥልሃለሁ።",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ እርዳታ\n"
        "1) Receipt Number ላክ\n"
        "2) ወይም Telebirr SMS Link ላክ\n"
        "ምሳሌ: DGH9WN4E4H"
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
        await query.message.reply_text("Receipt Number ላክ እና እመርምረዋለሁ።")

# ======================
# RECEIPT CHECK
# ======================
async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    match = re.search(r"receipt/([A-Z0-9]+)", text, re.IGNORECASE)
    receipt = match.group(1) if match else text
    
    status = await update.message.reply_text("🔍 Receipt እየመረመርኩ...")
    
    if exists(receipt):
        await status.edit_text("⚠️ ይህ Receipt ከዚህ በፊት ተጠቅመዋል።")
        return
        
    result = verify(receipt)
    
    if not result:
        await status.edit_text("❌ Receipt አልተገኘም ወይም የተሳሳተ ነው።")
        return
        
    save(result)
    
    await status.edit_text(
        f"✅ Payment Verified\n\n"
        f"🧾 Receipt: {result.get('receipt', receipt)}\n"
        f"👤 Sender: {result.get('sender', 'Unknown')}\n"
        f"💰 Amount: {result.get('amount', '0.00')} ETB\n"
        f"📅 Date: {result.get('date', 'Unknown')}\n"
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
    """Gunicorn Worker ውስጥ ቦቱን ማስጀመር"""
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
                
        # ቦቱን ማስጀመር
        asyncio.run_coroutine_threadsafe(setup(), worker_loop)
        bot_initialized = True


# ======================
# FLASK WEBHOOK ROUTES
# ======================
@app.route("/")
def home():
    init_bot() # ለደህንነት እዚህም እናስነሳዋለን
    return "Telebirr Smart Bot is Running Successfully!"

@app.route("/webhook", methods=["POST"])
def webhook():
    init_bot() # አዲሱ Gunicorn worker Thread መፍጠሩን ማረጋገጫ
    
    data = request.get_json(force=True)
    if data:
        update = Update.de_json(data, telegram_app.bot)
        if worker_loop:
            # መልእክቱን ወደ worker's loop መላክ
            asyncio.run_coroutine_threadsafe(telegram_app.process_update(update), worker_loop)
            
    return "ok", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
