import os, json, time, random, asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters
from telegram.constants import ChatAction
from google import genai
from datetime import datetime

# ================= LOAD ENV =================
load_dotenv()
BOT_TOKEN = "8563448359:AAHTVliW8IzzcNTVCz1dGRCSqPcSLjFaYNM"
GEMINI_API_KEY =  "AIzaSyCKwJNL6naE1DnQEVc_aQVXER5_KZOpKoQ"
OWNER_ID = 8236525737
BOT_USERNAME = "yourAkshabot"

client = genai.Client(api_key=GEMINI_API_KEY)

# ================= FILES =================
MEMORY_FILE = "memory.json"
MUTED_FILE = "muted.json"
GROUPS_FILE = "groups.json"
ANALYTICS_FILE = "analytics.json"

LAST_MSG = {}

# ================= HELPERS =================
def load_json(file, default):
    if not os.path.exists(file):
        return default
    with open(file, "r") as f:
        return json.load(f)

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=2)

# ================= MOOD =================
def get_mood():
    hour = datetime.now().hour
    if hour >= 23 or hour < 6:
        return random.choice(["sleepy", "low-energy"])
    return random.choice(["sweet", "rude", "playful", "neutral"])

# ================= PROMPT =================
def build_prompt(user, text, memory, mood):
    convo = "\n".join(memory[-5:])
    return f"""
You are a girl named Aksha. Act like a real human.

Traits:
- Indian modern girl
- Slightly rude, confident
- Casual flirting
- Natural Hinglish
- Short replies
- Rare emojis

Mood: {mood}

Conversation:
{convo}

User ({user}): {text}
Aksha:
"""

# ================= BROADCAST CORE =================
async def broadcast_text(context, text):
    users = load_json(MEMORY_FILE, {})
    groups = load_json(GROUPS_FILE, {})

    sent, failed = 0, 0

    for uid in users:
        try:
            await context.bot.send_message(int(uid), text)
            sent += 1
            await asyncio.sleep(0.3)
        except:
            failed += 1

    for gid in groups:
        try:
            await context.bot.send_message(int(gid), text)
            sent += 1
            await asyncio.sleep(0.4)
        except:
            failed += 1

    analytics = load_json(ANALYTICS_FILE, [])
    analytics.append({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "type": "text",
        "sent": sent,
        "failed": failed,
        "users": len(users),
        "groups": len(groups)
    })
    save_json(ANALYTICS_FILE, analytics)

    return sent, failed

# ================= MAIN HANDLER =================
async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return

    chat = update.effective_chat
    uid = str(msg.from_user.id)
    text = msg.text.strip() if msg.text else ""

    memory = load_json(MEMORY_FILE, {})
    muted = load_json(MUTED_FILE, {})
    groups = load_json(GROUPS_FILE, {})

    # ================= GROUP SAVE =================
    if chat.type in ["group", "supergroup"]:
        if str(chat.id) not in groups:
            groups[str(chat.id)] = {
                "title": chat.title,
                "added_at": time.time()
            }
            save_json(GROUPS_FILE, groups)

    # ================= OWNER COMMANDS =================
    if msg.from_user.id == OWNER_ID:

        if text.startswith("/broadcast_text"):
            msg_text = text.replace("/broadcast_text", "").strip()
            if not msg_text:
                await msg.reply_text("Message likh 😒")
                return

            await msg.reply_text("📡 Broadcasting...")
            sent, failed = await broadcast_text(context, msg_text)
            await msg.reply_text(f"✅ Done\nSent: {sent}\nFailed: {failed}")
            return

        if text == "/broadcast_stats":
            data = load_json(ANALYTICS_FILE, [])
            if not data:
                await msg.reply_text("No data yet")
                return
            last = data[-1]
            await msg.reply_text(
                f"📊 Last Broadcast\n"
                f"🕒 {last['time']}\n"
                f"📤 Sent: {last['sent']}\n"
                f"❌ Failed: {last['failed']}\n"
                f"👤 Users: {last['users']}\n"
                f"👥 Groups: {last['groups']}"
            )
            return

        if text == "/broadcast_photo" and msg.reply_to_message:
            photo = msg.reply_to_message.photo
            if not photo:
                return
            file_id = photo[-1].file_id
            caption = msg.reply_to_message.caption or ""
            users = load_json(MEMORY_FILE, {})
            groups = load_json(GROUPS_FILE, {})

            for uid in users:
                try:
                    await context.bot.send_photo(int(uid), file_id, caption=caption)
                    await asyncio.sleep(0.3)
                except:
                    pass

            for gid in groups:
                try:
                    await context.bot.send_photo(int(gid), file_id, caption=caption)
                    await asyncio.sleep(0.4)
                except:
                    pass

            await msg.reply_text("🖼️ Image broadcast done")
            return

    # ================= MUTED =================
    if uid in muted:
        return

    # ================= ANTI SPAM =================
    now = time.time()
    if uid in LAST_MSG and now - LAST_MSG[uid] < 3:
        return
    LAST_MSG[uid] = now

    # ================= GROUP SMART MODE =================
    if chat.type in ["group", "supergroup"]:
        if not (
            msg.reply_to_message
            or f"@{BOT_USERNAME.lower()}" in text.lower()
        ):
            return

    # ================= MEMORY =================
    if uid not in memory:
        memory[uid] = {"name": msg.from_user.first_name, "history": []}

    memory[uid]["history"].append(f"User: {text}")
    memory[uid]["history"] = memory[uid]["history"][-5:]
    save_json(MEMORY_FILE, memory)

    # ================= AI RESPONSE =================
    mood = get_mood()
    prompt = build_prompt(memory[uid]["name"], text, memory[uid]["history"], mood)

    await context.bot.send_chat_action(chat.id, ChatAction.TYPING)
    await asyncio.sleep(random.uniform(1.5, 3))

    try:
        res = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[{"role": "user", "parts": [{"text": prompt}]}]
        )
        reply_text = res.text[:300]
        memory[uid]["history"].append(f"Aksha: {reply_text}")
        save_json(MEMORY_FILE, memory)
        await msg.reply_text(reply_text)
    except:
        await msg.reply_text("Mood off hai 😏")

# ================= RUN =================
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, reply))
    print("🔥 Aksha Bot Running...")
    app.run_polling()

if __name__ == "__main__":
    main()
