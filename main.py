import asyncio
import signal
import nest_asyncio
from datetime import datetime, timedelta
from collections import defaultdict, deque

from telegram import Update, ChatPermissions, ChatMember
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.error import TelegramError

# ✅ Bot token & Webhook URL
TOKEN = "7698290595:AAHO-M-q2_D3wMUYDprq00jaZ_Gk1CG2ZqM"
WEBHOOK_URL = "https://msg-deleti.koyeb.app"
PORT = 8080

# 🛠 Settings
delete_delays = {}
admin_only_mode = {}
NSFW_KEYWORDS = {"sex", "porn", "nude", "xxx", "onlyfans", "boobs", "dick", "milf", "blowjob", "hentai"}
flood_enabled = defaultdict(lambda: False)
msg_logs = defaultdict(lambda: deque(maxlen=10))
MAX_MSG = 5
WINDOW = 5
warnings = defaultdict(lambda: defaultdict(int))  # chat_id -> user_id -> warn_count

# 🔐 Admin check
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member: ChatMember = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        return member.status in ("administrator", "creator")
    except TelegramError:
        return False

# 🧱 Time parser
def parse_time(time_str: str) -> int:
    unit = time_str[-1]
    value = int(time_str[:-1])
    return value * {"s": 1, "m": 60, "h": 3600, "d": 86400}.get(unit, 60)

# 📜 Commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome! Use /help to view commands.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛠 Commands:\n"
        "/start\n/help\n/settimer <sec>\n/off\n/status\n/onlyadminon\n/info\n"
        "/antiflood_on\n/antiflood_off\n/antiflood\n"
        "/ban (reply)\n/kick (reply)\n/mute (reply)\n/unmute (reply)\n"
        "/tempmute <duration>\n/tempban <duration>\n/warn\n/resetwarn"
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

# 👮 Moderation Commands
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return
    user = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    if user:
        await context.bot.ban_chat_member(update.effective_chat.id, user.id)
        await update.message.reply_text(f"🔨 Banned {user.full_name}")

async def kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return
    user = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    if user:
        await context.bot.ban_chat_member(update.effective_chat.id, user.id)
        await context.bot.unban_chat_member(update.effective_chat.id, user.id)
        await update.message.reply_text(f"👢 Kicked {user.full_name}")

async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return
    user = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    if user:
        await context.bot.restrict_chat_member(
            update.effective_chat.id, user.id,
            permissions=ChatPermissions(can_send_messages=False)
        )
        await update.message.reply_text(f"🔇 Muted {user.full_name}")

async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return
    user = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    if user:
        await context.bot.restrict_chat_member(
            update.effective_chat.id, user.id,
            permissions=ChatPermissions(can_send_messages=True)
        )
        await update.message.reply_text(f"🔊 Unmuted {user.full_name}")

async def tempmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return
    try:
        duration = parse_time(context.args[0])
        user = update.message.reply_to_message.from_user
        await context.bot.restrict_chat_member(
            update.effective_chat.id, user.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=datetime.utcnow() + timedelta(seconds=duration)
        )
        await update.message.reply_text(f"🔇 Muted for {context.args[0]}")
    except:
        await update.message.reply_text("⚠️ Usage: /tempmute <5m/1h>")

async def tempban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return
    try:
        duration = parse_time(context.args[0])
        user = update.message.reply_to_message.from_user
        await context.bot.ban_chat_member(
            update.effective_chat.id, user.id,
            until_date=datetime.utcnow() + timedelta(seconds=duration)
        )
        await update.message.reply_text(f"🔨 Banned for {context.args[0]}")
    except:
        await update.message.reply_text("⚠️ Usage: /tempban <5m/1h>")

async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return
    user = update.message.reply_to_message.from_user
    cid, uid = update.effective_chat.id, user.id
    warnings[cid][uid] += 1
    count = warnings[cid][uid]
    await update.message.reply_text(f"⚠️ Warning ({count}/3)")
    if count >= 3:
        await context.bot.restrict_chat_member(
            cid, uid,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=datetime.utcnow() + timedelta(minutes=10)
        )
        warnings[cid][uid] = 0
        await update.message.reply_text("🚫 Muted 10 mins after 3 warnings")

async def resetwarn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return
    user = update.message.reply_to_message.from_user
    warnings[update.effective_chat.id][user.id] = 0
    await update.message.reply_text("✅ Warnings reset")

# ✂️ Auto-delete and filters
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    chat_id, user_id = msg.chat_id, msg.from_user.id
    now = datetime.utcnow()

    if flood_enabled[chat_id]:
        msg_logs[(chat_id, user_id)].append(now)
        recent = [t for t in msg_logs[(chat_id, user_id)] if now - t < timedelta(seconds=WINDOW)]
        if len(recent) > MAX_MSG:
            await msg.delete()
            return

    if admin_only_mode.get(chat_id) and not await is_admin(update, context):
        await msg.delete(); return

    if msg.text and any(word in msg.text.lower() for word in NSFW_KEYWORDS):
        await msg.delete(); return

    if msg.photo or msg.video or msg.sticker or msg.animation or msg.document:
        await msg.delete(); return

    delay = delete_delays.get(chat_id)
    if delay:
        await asyncio.sleep(delay)
        try:
            await context.bot.delete_message(chat_id, msg.message_id)
        except: pass

# 🧍 Welcome / Goodbye
async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for user in update.message.new_chat_members:
        await update.message.reply_text(f"👋 Welcome {user.mention_html()}!", parse_mode='HTML')

async def goodbye(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.left_chat_member
    if user:
        await update.message.reply_text(f"👋 {user.full_name} left.")

# ✏️ Delete edited messages (non-admins)
async def delete_edited_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    edited_msg = update.edited_message
    if not edited_msg: return
    try:
        member = await context.bot.get_chat_member(edited_msg.chat_id, edited_msg.from_user.id)
        if member.status in ("administrator", "creator"): return
        await context.bot.delete_message(chat_id=edited_msg.chat_id, message_id=edited_msg.message_id)
    except: pass

# 🚀 App Setup
app = ApplicationBuilder().token(TOKEN).build()

# 📌 Handlers
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CommandHandler("settimer", settimer))
app.add_handler(CommandHandler("off", turn_off))
app.add_handler(CommandHandler("status", status))
app.add_handler(CommandHandler("onlyadminon", onlyadminon))
app.add_handler(CommandHandler("info", info))
app.add_handler(CommandHandler("ban", ban))
app.add_handler(CommandHandler("kick", kick))
app.add_handler(CommandHandler("mute", mute))
app.add_handler(CommandHandler("unmute", unmute))
app.add_handler(CommandHandler("tempmute", tempmute))
app.add_handler(CommandHandler("tempban", tempban))
app.add_handler(CommandHandler("warn", warn))
app.add_handler(CommandHandler("resetwarn", resetwarn))
app.add_handler(MessageHandler(filters.ALL, handle_message))
app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))
app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, goodbye))
app.add_handler(MessageHandler(filters.UpdateType.EDITED_MESSAGE, delete_edited_message))

# 🌐 Webhook with graceful shutdown
nest_asyncio.apply()
loop = asyncio.get_event_loop()

def _shutdown_signal():
    print("⚠️ Gracefully shutting down...")
    loop.stop()

signal.signal(signal.SIGINT, lambda s, f: _shutdown_signal())
signal.signal(signal.SIGTERM, lambda s, f: _shutdown_signal())

async def main():
    await app.initialize()
    await app.start()
    await app.updater.start_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=WEBHOOK_URL
    )
    print("🚀 Bot is live")

    try:
        await asyncio.Future()
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()
        print("🛑 Bot shutdown complete")

loop.run_until_complete(main())
    
