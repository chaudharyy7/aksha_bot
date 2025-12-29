import os, json, time, random, asyncio
from datetime import datetime
from dotenv import load_dotenv

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    Application,
    MessageHandler,
    ContextTypes,
    filters
)
from telegram.constants import ChatAction
from google import genai

# ================= LOAD ENV =================
load_dotenv()

BOT_TOKEN = "8563448359:AAHTVliW8IzzcNTVCz1dGRCSqPcSLjFaYNM"
GEMINI_API_KEY = "AIzaSyCKwJNL6naE1DnQEVc_aQVXER5_KZOpKoQ"
OWNER_ID = 8236525737
BOT_USERNAME = "yourAkshabot"

client = genai.Client(api_key=GEMINI_API_KEY)

# ================= PATHS =================
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

USERS_FILE = f"{DATA_DIR}/users.json"
GROUPS_FILE = f"{DATA_DIR}/groups.json"
ADMINS_FILE = f"{DATA_DIR}/admins.json"
BLOCKED_FILE = f"{DATA_DIR}/blocked.json"
BANNED_WORDS_FILE = f"{DATA_DIR}/banned_words.json"
ANALYTICS_FILE = f"{DATA_DIR}/analytics.json"
SETTINGS_FILE = f"{DATA_DIR}/settings.json"
SCHEDULE_FILE = f"{DATA_DIR}/schedule.json"

LAST_MSG = {}

# ================= DEFAULTS =================
DEFAULT_SETTINGS = {
    "bot_paused": False,
    "ai_enabled": True,
    "forced_mood": None,
    "reply_length": "short"
}

# ================= HELPERS =================
def load_json(file, default):
    if not os.path.exists(file):
        return default
    with open(file, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def is_admin(uid: int):
    admins = load_json(ADMINS_FILE, [])
    return uid == OWNER_ID or uid in admins

# ================= MOOD =================
def get_mood():
    hour = datetime.now().hour
    if hour >= 23 or hour < 6:
        return random.choice(["sleepy", "low-energy"])
    return random.choice(["sweet", "rude", "playful", "neutral"])

# ================= PROMPT =================
def build_prompt(user, text, history, mood):
    convo = "\n".join(history[-5:])
    return f"""
You are a girl named Aksha. Act like a real human.

Traits:
- Modern Indian girl
- Confident, slightly rude
- Casual flirting with emoji
- Natural Hinglish
- Short replies
- Rare emojis

Mood: {mood}

Conversation:
{convo}

User ({user}): {text}
Aksha:
"""

# ================= BROADCAST =================
async def broadcast_all(context, text, reply_markup=None):
    users = load_json(USERS_FILE, {})
    groups = load_json(GROUPS_FILE, {})

    sent = failed = 0

    for uid in users:
        try:
            await context.bot.send_message(int(uid), text, reply_markup=reply_markup)
            sent += 1
            await asyncio.sleep(0.3)
        except:
            failed += 1

    for gid in groups:
        try:
            await context.bot.send_message(int(gid), text, reply_markup=reply_markup)
            sent += 1
            await asyncio.sleep(0.4)
        except:
            failed += 1

    analytics = load_json(ANALYTICS_FILE, [])
    analytics.append({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sent": sent,
        "failed": failed,
        "users": len(users),
        "groups": len(groups)
    })
    save_json(ANALYTICS_FILE, analytics)

    return sent, failed

# ================= SCHEDULER =================
async def scheduler(app):
    while True:
        tasks = load_json(SCHEDULE_FILE, [])
        now = datetime.now().strftime("%H:%M")

        for task in tasks:
            if task["time"] == now and not task.get("done"):
                await broadcast_all(app.bot, task["msg"])
                task["done"] = True

        save_json(SCHEDULE_FILE, tasks)
        await asyncio.sleep(60)

# ================= MAIN HANDLER =================
async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return

    chat = update.effective_chat
    uid = msg.from_user.id
    text = msg.text.strip() if msg.text else ""

    users = load_json(USERS_FILE, {})
    groups = load_json(GROUPS_FILE, {})
    blocked = load_json(BLOCKED_FILE, [])
    banned_words = load_json(BANNED_WORDS_FILE, [])
    settings = load_json(SETTINGS_FILE, DEFAULT_SETTINGS)

    # ================= BLOCKED =================
    if uid in blocked:
        return

    # ================= SAVE USER =================
    if str(uid) not in users:
        users[str(uid)] = {
            "name": msg.from_user.first_name,
            "history": []
        }
        save_json(USERS_FILE, users)

    # ================= SAVE GROUP =================
    if chat.type in ["group", "supergroup"]:
        if str(chat.id) not in groups:
            groups[str(chat.id)] = {
                "title": chat.title,
                "added_at": time.time()
            }
            save_json(GROUPS_FILE, groups)

    # ================= FORWARD REPLIES TO OWNER =================
    if (
        msg.reply_to_message
        and msg.reply_to_message.from_user
        and msg.reply_to_message.from_user.is_bot
        and uid != OWNER_ID
    ):
        await context.bot.send_message(
            OWNER_ID,
            f"📩 Reply from {msg.from_user.first_name} (@{msg.from_user.username})\n\n{text}"
        )

    # ================= OWNER COMMANDS =================
    if is_admin(uid):

        if text == "/pause_bot":
            settings["bot_paused"] = True
            save_json(SETTINGS_FILE, settings)
            await msg.reply_text("⏸ Bot paused")
            return

        if text == "/resume_bot":
            settings["bot_paused"] = False
            save_json(SETTINGS_FILE, settings)
            await msg.reply_text("▶️ Bot resumed")
            return

        if text.startswith("/broadcast_text"):
            content = text.replace("/broadcast_text", "").strip()
            sent, failed = await broadcast_all(context, content)
            await msg.reply_text(f"✅ Broadcast done\nSent: {sent}\nFailed: {failed}")
            return

        if text.startswith("/broadcast_button"):
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔥 Join Now", url="https://t.me/yourchannel")]
            ])
            sent, failed = await broadcast_all(context, "🔥 New Offer Live", keyboard)
            await msg.reply_text("🔘 Button broadcast sent")
            return

        if text.startswith("/sendto"):
            _, tid, msg_txt = text.split(maxsplit=2)
            await context.bot.send_message(int(tid), msg_txt)
            await msg.reply_text("✅ Sent")
            return

        if text.startswith("/add_admin"):
            aid = int(text.split()[1])
            admins = load_json(ADMINS_FILE, [])
            admins.append(aid)
            save_json(ADMINS_FILE, admins)
            await msg.reply_text("✅ Admin added")
            return

        if text.startswith("/ban_word"):
            word = text.split()[1]
            banned_words.append(word.lower())
            save_json(BANNED_WORDS_FILE, banned_words)
            await msg.reply_text("🚫 Word banned")
            return

    # ================= BOT PAUSED =================
    if settings["bot_paused"]:
        return

    # ================= BANNED WORD FILTER =================
    for w in banned_words:
        if w in text.lower():
            return

    # ================= ANTI SPAM =================
    now = time.time()
    if uid in LAST_MSG and now - LAST_MSG[uid] < 3:
        return
    LAST_MSG[uid] = now

    # ================= GROUP SMART MODE =================
    if chat.type in ["group", "supergroup"]:
        mentioned = f"@{BOT_USERNAME.lower()}" in text.lower()
        replied = msg.reply_to_message and msg.reply_to_message.from_user.is_bot
        random_reply = random.random() < 0.7

        if not (mentioned or replied or random_reply):
            return

    # ================= AI RESPONSE =================
    if not settings["ai_enabled"]:
        await msg.reply_text("Aksha busy hai 😒")
        return

    mood = settings["forced_mood"] or get_mood()
    history = users[str(uid)]["history"]

    prompt = build_prompt(users[str(uid)]["name"], text, history, mood)

    await context.bot.send_chat_action(chat.id, ChatAction.TYPING)
    await asyncio.sleep(random.uniform(1.5, 3))

    try:
        res = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[{"role": "user", "parts": [{"text": prompt}]}]
        )
        reply_text = res.text[:300]
        history.append(f"User: {text}")
        history.append(f"Aksha: {reply_text}")
        users[str(uid)]["history"] = history[-10:]
        save_json(USERS_FILE, users)
        await msg.reply_text(reply_text)
    except:
        await msg.reply_text("Mood off hai 😏")

# ================= RUN =================
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, reply))

    # ✅ start scheduler safely (NO JobQueue)
    app.post_init = on_startup

    print("🔥 Aksha Bot running...")
    app.run_polling()
