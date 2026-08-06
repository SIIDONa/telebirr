import os
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
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")  # ምሳሌ: https://your-app.onrender.com
PORT = int(os.environ.get("PORT", "5000"))   # Render ራሱ ፖርት ይሰጠዋል

# ያንተን መረጃ አስገባ
MY_RECEIVER_NAME = "Melaku Abraham Ersedo"
MY_RECEIVER_PHONE = "2519XXXX4952" 

# ======================
# COMMANDS & HANDLERS
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

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "verify":
        await query.message.reply_text("🧾 እባክዎ Receipt Number ወይም Link ላክ።")
    elif query.data == "help":
        await query.message.reply_text("የከፈሉበትን ሪሲፕት ቁጥር ይላኩ እና እመርምረዋለሁ።")

async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    status_msg = await update.message.reply_text("🔍 ሪሲፕቱን እያጣራሁ ነው...")
    
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
    
    if exists(receipt_id):
        await status_msg.edit_text(f"⚠️ ይህ ሪሲፕት ({receipt_id}) ከዚህ በፊት ጥቅም ላይ ውሏል!")
        return
        
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
# START NATIVE WEBHOOK
# ======================
if __name__ == "__main__":
    print("✅ Starting Database...")
    init_db()
    
    print("✅ Building Telegram Application...")
    telegram_app = Application.builder().token(TOKEN).build()
    
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CommandHandler("help", help_command))
    telegram_app.add_handler(CallbackQueryHandler(button))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check))
    
    print(f"🌍 Starting Built-in Webhook on port {PORT}...")
    
    # የቴሌግራምን Native ዌብሁክ እናስነሳለን (ምንም Gunicorn/Flask አያስፈልግም)
    telegram_app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=WEBHOOK_URL
    )
