import os
import logging
import asyncio
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
)
from aiohttp import web
from apscheduler.schedulers.asyncio import AsyncIOScheduler

BOT_TOKEN = os.environ.get("7698290595:AAHO-M-q2_D3wMUYDprq00jaZ_Gk1CG2ZqM")
WEBHOOK_URL = "https://auto-delete.koyeb.app"
PORT = int(os.environ.get("PORT", 8080))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

chat_delete_times = {}
scheduler = AsyncIOScheduler()
scheduler.start()

async def set_delete_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1 or not context.args[0].isdigit():
        await update.message.reply_text("Usage: /setdeletetime <seconds>")
        return
    seconds = int(context.args[0])
    chat_id = update.effective_chat.id
    chat_delete_times[chat_id] = seconds
    await update.message.reply_text(f"Auto-delete time set to {seconds} seconds.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if chat_id not in chat_delete_times:
        return
    delete_after = chat_delete_times[chat_id]
    delete_time = datetime.now() + timedelta(seconds=delete_after)
    scheduler.add_job(
        delete_message,
        'date',
        run_date=delete_time,
        args=[context.application, chat_id, update.message.message_id],
        id=f"{chat_id}_{update.message.message_id}",
        replace_existing=True
    )

async def delete_message(app, chat_id, message_id):
    try:
        await app.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        logger.warning(f"Failed to delete message {message_id}: {e}")

async def webhook_handler(request):
    data = await request.json()
    await request.app["bot"].update_queue.put(Update.de_json(data, request.app["bot"].bot))
    return web.Response()

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("setdeletetime", set_delete_time))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    await app.bot.set_webhook(f"{WEBHOOK_URL}/webhook")
    logger.info(f"Webhook set to {WEBHOOK_URL}/webhook")

    web_app = web.Application()
    web_app["bot"] = app
    web_app.add_routes([web.post("/webhook", webhook_handler)])

    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    logger.info(f"Bot server started on port {PORT}")
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
