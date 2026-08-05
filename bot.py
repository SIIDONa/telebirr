import os
import re
from flask import Flask, request

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters
)

from database import init_db, exists, save
from verifier import verify


TOKEN = os.environ["BOT_TOKEN"]

WEBHOOK_URL = os.environ["WEBHOOK_URL"]

app = Flask(__name__)

telegram_app = Application.builder()\
    .token(TOKEN)\
    .build()


async def start(update, context):
    await update.message.reply_text(
        "👋 Telebirr Receipt Verifier\nSend receipt number."
    )


async def check(update, context):

    text = update.message.text.strip()

    match = re.search(
        r"receipt/([A-Z0-9]+)",
        text
    )

    receipt = match.group(1) if match else text


    if exists(receipt):
        await update.message.reply_text(
            "⚠️ Already verified"
        )
        return


    result = verify(receipt)

    if not result:
        await update.message.reply_text(
            "❌ Invalid receipt"
        )
        return


    save(result)


    await update.message.reply_text(
f"""
✅ Verified

🧾 Receipt:
{result['receipt']}

💰 Amount:
{result['amount']} ETB

📅 Date:
{result['date']}
"""
    )


telegram_app.add_handler(
    CommandHandler("start", start)
)

telegram_app.add_handler(
    MessageHandler(
        filters.TEXT,
        check
    )
)


@app.route("/", methods=["GET"])
def home():
    return "Telebirr Bot Running"


@app.route("/webhook", methods=["POST"])
def webhook():

    update = Update.de_json(
        request.json,
        telegram_app.bot
    )

    telegram_app.update_queue.put_nowait(update)

    return "ok"


@app.before_first_request
def setup():

    init_db()

    telegram_app.bot.set_webhook(
        url=f"{WEBHOOK_URL}/webhook"
    )


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT",5000))
    )
