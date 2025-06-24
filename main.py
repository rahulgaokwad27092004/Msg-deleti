import asyncio
from datetime import datetime, timedelta
from collections import defaultdict, deque

from telegram import Update, ChatMember
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.error import TelegramError

# ✅ Bot token & Webhook URL (filled in)
TOKEN = "7698290595:AAHO-M-q2_D3wMUYDprq00jaZ_Gk1CG2ZqM"
WEBHOOK_URL = "https://msg-deleti.koyeb.app"
PORT = 8080  # Default Koyeb port

# 🛠 Settings
delete_delays = {}
admin_only_mode = {}
NSFW_KEYWORDS = {"sex", "porn", "nude", "xxx", "onlyfans", "boobs", "dick", "milf", "blowjob", "hentai"}
flood_enabled = defaultdict(lambda: False)
msg_logs = defaultdict(lambda: deque(maxlen=10))
MAX_MSG = 5
WINDOW = 5

async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member: ChatMember = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        return member.status in ("administrator", "creator")
    except TelegramError:
        return False

# Commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome! Use /help to view commands.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛠 Commands:\n"
        "/start\n/help\n/settimer <sec>\n/off\n/status\n/onlyadminon\n/info\n"
        "/antiflood_on\n/antiflood_off\n/antiflood"
    )

async def settimer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("🚫 Admin only.")
    try:
        delay = int(context.args[0])
        delete_delays[update.effective_chat.id] = delay
        await update.message.reply_text(f"✅ Auto-delete after {delay} seconds.")
    except:
        await update.message.reply_text("⚠️ Usage: /settimer <seconds>")

async def turn_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("🚫 Admin only.")
    delete_delays.pop(update.effective_chat.id, None)
    await update.message.reply_text("🛑 Auto-delete turned OFF.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("🚫 Admin only.")
    chat_id = update.effective_chat.id
    await update.message.reply_text(
        f"🧾 Status:\nTimer: {delete_delays.get(chat_id, 'OFF')}\n"
        f"Admin-Only: {admin_only_mode.get(chat_id, False)}\n"
        f"Anti-Flood: {'ON' if flood_enabled[chat_id] else 'OFF'}"
    )

async def onlyadminon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return await update.message.reply_text("🚫 Admin only.")
    admin_only_mode[update.effective_chat.id] = True
    await update.message.reply_text("🔒 Admin-only chat enabled.")

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    await update.message.reply_text(f"ℹ️ Group: {chat.title}\nID: {chat.id}\nType: {chat.type}")

async def antiflood_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return
    flood_enabled[update.effective_chat.id] = True
    await update.message.reply_text("🛡️ Anti-flood enabled.")

async def antiflood_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return
    flood_enabled[update.effective_chat.id] = False
    await update.message.reply_text("🚫 Anti-flood disabled.")

async def antiflood_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return
    status = "ON" if flood_enabled[update.effective_chat.id] else "OFF"
    await update.message.reply_text(f"🛡️ Anti-flood is {status}.")

# Message handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    chat_id = msg.chat_id
    user_id = msg.from_user.id

    # Anti-flood
    if flood_enabled[chat_id]:
        now = datetime.utcnow()
        msg_logs[(chat_id, user_id)].append(now)
        if len([t for t in msg_logs[(chat_id, user_id)] if now - t < timedelta(seconds=WINDOW)]) > MAX_MSG:
            await msg.delete()
            return

    # Admin-only mode
    if admin_only_mode.get(chat_id) and not await is_admin(update, context):
        await msg.delete()
        return

    # NSFW detection
    if msg.text and any(word in msg.text.lower() for word in NSFW_KEYWORDS):
        await msg.delete()
        return

    if msg.photo or msg.video or msg.sticker or msg.animation or msg.document:
        await msg.delete()
        return

    # Auto-delete
    delay = delete_delays.get(chat_id)
    if delay:
        await asyncio.sleep(delay)
        try:
            await context.bot.delete_message(chat_id, msg.message_id)
        except:
            pass

# Bot run
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CommandHandler("settimer", settimer))
app.add_handler(CommandHandler("off", turn_off))
app.add_handler(CommandHandler("status", status))
app.add_handler(CommandHandler("onlyadminon", onlyadminon))
app.add_handler(CommandHandler("info", info))
app.add_handler(CommandHandler("antiflood_on", antiflood_on))
app.add_handler(CommandHandler("antiflood_off", antiflood_off))
app.add_handler(CommandHandler("antiflood", antiflood_status))
app.add_handler(MessageHandler(filters.ALL, handle_message))

app.run_webhook(
    listen="0.0.0.0",
    port=PORT,
    webhook_url=WEBHOOK_URL
                  )
    
