import asyncio
from telegram import Update, ChatMember
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.error import TelegramError

# 🔐 Your real bot token and webhook URL (replace with your actual Koyeb URL)
TOKEN = "7698290595:AAHO-M-q2_D3wMUYDprq00jaZ_Gk1CG2ZqM"
WEBHOOK_URL = "https://msg-deleti.koyeb.app"
PORT = 8080

delete_delays = {}
admin_only_mode = {}

# Check if user is admin
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member: ChatMember = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        return member.status in ("administrator", "creator")
    except TelegramError:
        return False

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome! Use /help to see available commands.")

# /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🛠 Available Commands:\n\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "/settimer <seconds> - Set message auto-delete time ⏲️ (admin only)\n"
        "/off - Turn off auto-delete ❌ (admin only)\n"
        "/status - Show current settings 📊 (admin only)\n"
        "/onlyadminon - Delete non-admin messages only 🛡️ (admin only)\n"
        "/info - Show group and bot info ℹ️"
    )
    await update.message.reply_text(help_text)

# /settimer
async def settimer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("🚫 Only admins can use this command.")
    try:
        delay = int(context.args[0])
        delete_delays[update.effective_chat.id] = delay
        await update.message.reply_text(f"✅ Messages will auto-delete after {delay} seconds.")
    except (IndexError, ValueError):
        await update.message.reply_text("⚠️ Usage: /settimer <seconds>")

# /off
async def turn_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("🚫 Only admins can use this command.")
    delete_delays.pop(update.effective_chat.id, None)
    await update.message.reply_text("🛑 Auto-delete is now OFF.")

# /status
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("🚫 Only admins can use this command.")
    chat_id = update.effective_chat.id
    timer = delete_delays.get(chat_id, "OFF")
    mode = "ON" if admin_only_mode.get(chat_id) else "OFF"
    await update.message.reply_text(f"📊 Status:\nAuto-delete: {timer}\nAdmin-only mode: {mode}")

# /onlyadminon
async def onlyadminon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("🚫 Only admins can use this command.")
    chat_id = update.effective_chat.id
    admin_only_mode[chat_id] = True
    await update.message.reply_text("🛡️ Admin-only mode enabled. Non-admin messages will be deleted.")

# /info
async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    await update.message.reply_text(
        f"ℹ️ Group Info:\n"
        f"Title: {chat.title}\n"
        f"ID: {chat.id}\n"
        f"Type: {chat.type}\n"
        f"Bot active in this group."
    )

# Message handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    delay = delete_delays.get(chat_id)
    admin_mode = admin_only_mode.get(chat_id, False)

    if admin_mode and not await is_admin(update, context):
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=update.message.message_id)
        except:
            pass
        return

    if delay:
        await asyncio.sleep(delay)
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=update.message.message_id)
        except:
            pass

# Build bot
app = ApplicationBuilder().token(TOKEN).build()

# Add handlers
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CommandHandler("settimer", settimer))
app.add_handler(CommandHandler("off", turn_off))
app.add_handler(CommandHandler("status", status))
app.add_handler(CommandHandler("onlyadminon", onlyadminon))
app.add_handler(CommandHandler("info", info))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Start via webhook
app.run_webhook(
    listen="0.0.0.0",
    port=PORT,
    webhook_url=WEBHOOK_URL
    )
                 
