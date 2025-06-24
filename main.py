import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Bot Token and Webhook URL (hardcoded)
TOKEN = "7698290595:AAHO-M-q2_D3wMUYDprq00jaZ_Gk1CG2ZqM"
WEBHOOK_URL = "https://your-koyeb-app-name.koyeb.app"  # ← Replace with your actual deployed app URL
PORT = 8080  # Default for Koyeb

# Store deletion timers per chat
delete_delays = {}

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 I'm live on Webhook! Use /settimer <seconds> to auto-delete messages.")

# Set timer command
async def settimer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        delay = int(context.args[0])
        chat_id = update.effective_chat.id
        delete_delays[chat_id] = delay
        await update.message.reply_text(f"✅ Messages will auto-delete after {delay} seconds.")
    except (IndexError, ValueError):
        await update.message.reply_text("⚠️ Usage: /settimer <seconds>")

# Handle regular messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = message.chat_id
    delay = delete_delays.get(chat_id)

    if delay:
        await asyncio.sleep(delay)
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=message.message_id)
        except:
            pass  # silently ignore failures (e.g. no permission)

# Build app and add handlers
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("settimer", settimer))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Start webhook
app.run_webhook(
    listen="0.0.0.0",
    port=PORT,
    webhook_url=WEBHOOK_URL
)
