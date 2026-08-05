import os
import re
import asyncio
import threading
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
)

# እነዚህ ፋይሎች (database.py እና verifier.py) ከቦቱ ጋር አብረው መኖር አለባቸው
from database import init_db, exists, save
from verifier import verify

TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

app = Flask(__name__)

# ======================
# TELEGRAM APP SETUP
# ======================
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
# BACKGROUND LOOP (FIX)
# ======================
loop = asyncio.new_event_loop()

def start_background_loop(loop: asyncio.AbstractEventLoop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

# አዲስ Thread ከፍተን Event Loop እንዲሮጥ እናደርጋለን (ለ Gunicorn ተስማሚ ነው)
threading.Thread(target=start_background_loop, args=(loop,), daemon=True).start()

async def setup_telegram():
    init_db()  # ዳታቤዙን ማስጀመር
    await telegram_app.initialize()
    await telegram_app.start()
    
    if WEBHOOK_URL:
        # Webhook URL በማዘጋጀት ቴሌግራም መልእክቶችን ወደ እኛ ራውት እንዲልክ ማዘዝ
        await telegram_app.bot.set_webhook(f"{WEBHOOK_URL.rstrip('/')}/webhook")
        print(f"Webhook set to: {WEBHOOK_URL}/webhook")

# አፕሊኬሽኑ ሲነሳ Bot Setup እንዲደረግ ማዘዝ
asyncio.run_coroutine_threadsafe(setup_telegram(), loop)


# ======================
# FLASK WEBHOOK ROUTES
# ======================
@app.route("/")
def home():
    return "Telebirr Smart Bot is Running Successfully!"

@app.route("/webhook", methods=["POST"])
def webhook():
    # request.get_json(force=True) ቴሌግራም የሚልከውን ዳታ በአስተማማኝ ሁኔታ ይቀበላል
    data = request.get_json(force=True)
    if data:
        update = Update.de_json(data, telegram_app.bot)
        # Updateን ወደ ተዘጋጀው background loop መላክ
        asyncio.run_coroutine_threadsafe(telegram_app.process_update(update), loop)
    return "ok", 200

# ለአካባቢያዊ ቴስቲንግ (Render ላይ በ Gunicorn ስለሚሰራ ይህ አይነካም)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
