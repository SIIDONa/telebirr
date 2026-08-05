import re

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)

from config import BOT_TOKEN,ADMIN_ID
from database import *
from verifier import verify


async def start(update,context):

    await update.message.reply_text(
        """
👋 Telebirr Receipt Verifier

Send receipt number or SMS link.
"""
    )


async def check(update,context):

    msg=update.message.text.strip()


    match=re.search(
        r'receipt/([A-Z0-9]+)',
        msg
    )


    receipt=(
        match.group(1)
        if match
        else msg
    )


    if exists(receipt):

        await update.message.reply_text(
            "⚠️ Receipt already verified."
        )

        return


    await update.message.reply_text(
        "🔍 Checking..."
    )


    result=verify(receipt)


    if not result:

        await update.message.reply_text(
            "❌ Invalid receipt"
        )

        return


    save(result)


    await update.message.reply_text(
f"""
✅ Payment Verified

🧾 Receipt:
{result['receipt']}

👤 Sender:
{result['sender']}

💰 Amount:
{result['amount']} ETB

📅 Date:
{result['date']}

📌 Status:
{result['status']}
"""
)



async def stats(update,context):

    if update.effective_user.id != ADMIN_ID:
        return


    await update.message.reply_text(
        f"📊 Total Verified: {count()}"
    )



def main():

    init_db()


    app=Application.builder()\
    .token(BOT_TOKEN)\
    .build()


    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )


    app.add_handler(
        CommandHandler(
            "stats",
            stats
        )
    )


    app.add_handler(
        MessageHandler(
            filters.TEXT,
            check
        )
    )


    print("Bot started")

    app.run_polling()



if __name__=="__main__":
    main()
