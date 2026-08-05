import os
import re
import asyncio

from flask import Flask, request

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)

from database import init_db, exists, save
from verifier import verify


TOKEN = os.environ["BOT_TOKEN"]
WEBHOOK_URL = os.environ["WEBHOOK_URL"]


app = Flask(__name__)


telegram_app = Application.builder()\
    .token(TOKEN)\
    .build()



# ======================
# START
# ======================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard = [
        [
            InlineKeyboardButton(
                "🧾 Verify Receipt",
                callback_data="verify"
            )
        ],
        [
            InlineKeyboardButton(
                "ℹ️ Help",
                callback_data="help"
            )
        ]
    ]

    await update.message.reply_text(
        """
👋 ሰላም!

እኔ Telebirr Receipt Verification Bot ነኝ።

የTelebirr ክፍያዎን በReceipt Number ወይም SMS Link ማረጋገጥ እችላለሁ።

ከታች ይምረጡ።
""",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )



# ======================
# BUTTONS
# ======================

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()


    if query.data == "verify":

        await query.message.reply_text(
            """
🧾 Receipt Number ወይም Telebirr SMS Link ይላኩ።

ምሳሌ:
DGH9WN4E4H
"""
        )


    elif query.data == "help":

        await query.message.reply_text(
            """
ℹ️ Help

1. Telebirr SMS Receipt Link ይላኩ
ወይም
2. Receipt Number ብቻ ይላኩ

Bot ክፍያውን ያረጋግጣል።
"""
        )



# ======================
# VERIFY
# ======================

async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.strip()


    match = re.search(
        r"receipt/([A-Z0-9]+)",
        text
    )


    receipt = (
        match.group(1)
        if match
        else text
    )


    msg = await update.message.reply_text(
        "🔍 Receipt እየመረመርኩ ነው..."
    )


    if exists(receipt):

        await msg.edit_text(
            """
⚠️ ይህ Receipt ከዚህ በፊት ተረጋግጧል።
"""
        )

        return



    result = verify(receipt)



    if not result:

        await msg.edit_text(
            """
❌ Receipt አልተገኘም።

እባክዎ Receipt Number እንደገና ይላኩ።
"""
        )

        return



    save(result)



    await msg.edit_text(
f"""
✅ ክፍያ ተረጋግጧል

🧾 Receipt:
{result['receipt']}

👤 ላኪ:
{result['sender']}

💰 መጠን:
{result['amount']} ብር

📅 ቀን:
{result['date']}

📌 Status:
SUCCESS


ስለ Telebirr አጠቃቀምዎ እናመሰግናለን 🙏
"""
    )



# ======================
# WEBHOOK
# ======================

@app.route("/")
def home():

    return "Telebirr Smart Bot Running"



@app.route("/webhook", methods=["POST"])
def webhook():

    update = Update.de_json(
        request.json,
        telegram_app.bot
    )


    telegram_app.update_queue.put_nowait(update)


    return "ok"



# ======================
# INIT
# ======================

telegram_app.add_handler(
    CommandHandler(
        "start",
        start
    )
)


telegram_app.add_handler(
    CallbackQueryHandler(
        button
    )
)


telegram_app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        check
    )
)



async def setup():

    init_db()

    await telegram_app.initialize()

    await telegram_app.bot.set_webhook(
        f"{WEBHOOK_URL}/webhook"
    )


asyncio.run(setup())
