from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
)
from aiohttp import web
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
import logging
import os
import asyncio

# ✅ Get BOT_TOKEN from environment variables
BOT_TOKEN = os.environ.get("7698290595:AAHO-M-q2_D3wMUYDprq00jaZ_Gk1CG2ZqM")

# ✅ Default port and webhook URL
PORT = int(os.environ.get("PORT", 8080))
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "https://your-koyeb-app.koyeb.app")  # Replace this on Koyeb if needed

chat_delete_times = {}
scheduler = AsyncIOScheduler()
scheduler.start()

# ✅ Enable logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

# ✅ Command to set message auto-delete time
async def set_delete_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1 or not context.args[0].isdigit():
        await update.message.reply_text("Usage: /setdeletetime <seconds>")
        return
    seconds = int(context.args[0])
    chat_id = update.effective_chat.id
    chat_delete_times[chat_id] = seconds
    await update.message.reply_text(f"Messages will now be deleted after {seconds} seconds.")

# ✅ Message handler to schedule deletion
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = message.chat_id

    if chat_id not in chat_delete_times:
        return

    delete_after = chat_delete_times[chat_id]
    delete_time = datetime.now() + timedelta(seconds=delete_after)

    scheduler.add_job(
        delete_message,
        'date',
        run_date=delete_time,
        args=[context.application, chat_id, message.message_id],
        id=f"{chat_id}_{message.message_id}",
        replace_existing=True
    )

# ✅ Function to delete a message
async def delete_message(app, chat_id, message_id):
    try:
        await app.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        print(f"Error deleting message: {e}")

# ✅ Main async entry point
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("setdeletetime", set_delete_time))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    # ✅ Set webhook
    await app.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")

    # ✅ AIOHTTP server for webhook
    async def handler(request):
        data = await request.json()
        await app.update_queue.put(Update.de_json(data, app.bot))
        return web.Response()

    web_app = web.Application()
    web_app.add_routes([web.post("/webhook", handler)])
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    print(f"Bot running via webhook at {WEBHOOK_URL}/webhook")

    while True:
        await asyncio.sleep(3600)

# ✅ Run it
if __name__ == "__main__":
    asyncio.run(main())
    
