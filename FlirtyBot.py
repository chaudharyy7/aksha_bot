import os
import time
import random
import asyncio
from datetime import datetime
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters
from telegram.constants import ChatAction

import google.generativeai as genai
from pymongo import MongoClient

# ==================================================
# LOAD ENV
# ==================================================
load_dotenv()

BOT_TOKEN = "8563448359:AAEO9VHBxLQZkz48QpPlOZedWR5kzE183kI"
GEMINI_API_KEY = "AIzaSyATKQi_Yjj4H2ZXx4InRggWjWvOodvw3yk"
OWNER_ID = 8236525737
BOT_USERNAME = "yourAkshabot"
MONGO_URI = "mongodb+srv://mefirebase1115_db_user:f76qFi3OqJQsagU2@cluster0.wsppssu.mongodb.net/?appName=Cluster0"

# ==================================================
# MONGODB
# ==================================================
mongo = MongoClient(MONGO_URI)
db = mongo["aksha_bot"]

users_col = db["users"]        # user memory + premium
groups_col = db["groups"]      # groups
muted_col = db["muted"]        # muted users
analytics_col = db["analytics"]

# ==================================================
# GEMINI
# ==================================================
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# ==================================================
# RUNTIME MEMORY
# ==================================================
LAST_MSG = {}

# ==================================================
# MOOD ENGINE
# ==================================================
def get_mood():
    h = datetime.now().hour
    if h >= 23 or h < 6:
        return random.choice(["sleepy", "low-energy"])
    return random.choice(["sweet", "rude", "playful", "neutral"])

# ==================================================
# PROMPT
# ==================================================
def build_prompt(name, text, history, mood):
    convo = "\n".join(history[-5:])
    return (
        "You are Aksha, a modern Indian girl.\n"
        "Short Hinglish replies. Confident. Slightly rude. Light flirting.\n"
        f"Mood: {mood}\n\n"
        f"{convo}\n"
        f"User ({name}): {text}\n"
        "Aksha:"
    )

# ==================================================
# BROADCAST
# ==================================================
async def broadcast_text(context, text):
    sent, failed = 0, 0

    for u in users_col.find({}, {"_id": 1}):
        try:
            await context.bot.send_message(int(u["_id"]), text)
            sent += 1
            await asyncio.sleep(0.3)
        except:
            failed += 1

    for g in groups_col.find({}, {"_id": 1}):
        try:
            await context.bot.send_message(int(g["_id"]), text)
            sent += 1
            await asyncio.sleep(0.4)
        except:
            failed += 1

    analytics_col.insert_one({
        "time": datetime.now(),
        "sent": sent,
        "failed": failed
    })

    return sent, failed

# ==================================================
# MAIN HANDLER
# ==================================================
async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return

    chat = update.effective_chat
    user = msg.from_user
    uid = str(user.id)
    text = msg.text.strip() if msg.text else ""

    # ---------- SAVE GROUP ----------
    if chat.type in ["group", "supergroup"]:
        groups_col.update_one(
            {"_id": str(chat.id)},
            {"$set": {"title": chat.title}},
            upsert=True
        )

    # ---------- MUTED ----------
    if muted_col.find_one({"_id": uid}):
        return

    # ---------- LOAD USER ----------
    user_doc = users_col.find_one({"_id": uid}) or {
        "_id": uid,
        "name": user.first_name,
        "history": [],
        "premium": False
    }

    is_premium = user_doc.get("premium", False)

    # ---------- ANTI SPAM ----------
    if not is_premium:
        now = time.time()
        if uid in LAST_MSG and now - LAST_MSG[uid] < 3:
            return
        LAST_MSG[uid] = now

    # ---------- GROUP SMART MODE ----------
    if chat.type in ["group", "supergroup"]:
        if not (msg.reply_to_message or f"@{BOT_USERNAME}" in text.lower()):
            return

    # ==================================================
    # OWNER COMMANDS
    # ==================================================
    if user.id == OWNER_ID:

        # ---- MUTE ----
        if text.startswith("/mute"):
            parts = text.split()
            if len(parts) != 2:
                await msg.reply_text("Usage: /mute <user_id>")
                return
            muted_col.update_one(
                {"_id": parts[1]},
                {"$set": {"muted_at": datetime.now()}},
                upsert=True
            )
            await msg.reply_text("🔇 User muted")
            return

        # ---- UNMUTE ----
        if text.startswith("/unmute"):
            parts = text.split()
            if len(parts) != 2:
                await msg.reply_text("Usage: /unmute <user_id>")
                return
            muted_col.delete_one({"_id": parts[1]})
            await msg.reply_text("🔊 User unmuted")
            return

        # ---- SEND USER ----
        if text.startswith("/send_user"):
            parts = text.split(maxsplit=2)

            if msg.reply_to_message and len(parts) == 2:
                await context.bot.send_message(int(parts[1]), msg.reply_to_message.text)
                await msg.reply_text("✅ Message sent")
                return

            if len(parts) < 3:
                await msg.reply_text("Usage: /send_user <id> <message>")
                return

            await context.bot.send_message(int(parts[1]), parts[2])
            await msg.reply_text("✅ Message sent")
            return

        # ---- PREMIUM ADD ----
        if text.startswith("/premium_add"):
            parts = text.split()
            if len(parts) != 2:
                await msg.reply_text("Usage: /premium_add <user_id>")
                return
            users_col.update_one(
                {"_id": parts[1]},
                {"$set": {"premium": True}},
                upsert=True
            )
            await msg.reply_text("💎 Premium activated")
            return

        # ---- PREMIUM REMOVE ----
        if text.startswith("/premium_remove"):
            parts = text.split()
            if len(parts) != 2:
                await msg.reply_text("Usage: /premium_remove <user_id>")
                return
            users_col.update_one(
                {"_id": parts[1]},
                {"$set": {"premium": False}}
            )
            await msg.reply_text("❌ Premium removed")
            return

        # ---- BROADCAST ----
        if text.startswith("/broadcast_text"):
            message = text.replace("/broadcast_text", "").strip()
            if not message:
                await msg.reply_text("Message likh 😒")
                return
            await msg.reply_text("📡 Broadcasting...")
            sent, failed = await broadcast_text(context, message)
            await msg.reply_text(f"✅ Done\nSent: {sent}\nFailed: {failed}")
            return

    # ==================================================
    # USER MEMORY
    # ==================================================
    user_doc["history"].append(f"User: {text}")
    user_doc["history"] = user_doc["history"][-5:]

    users_col.update_one(
        {"_id": uid},
        {"$set": user_doc},
        upsert=True
    )

    # ==================================================
    # AI RESPONSE
    # ==================================================
    mood = get_mood()
    prompt = build_prompt(user_doc["name"], text, user_doc["history"], mood)

    await context.bot.send_chat_action(chat.id, ChatAction.TYPING)

    if not is_premium:
        await asyncio.sleep(random.uniform(1.5, 3))

    try:
        res = model.generate_content(prompt)
        reply_text = res.text[:300]

        user_doc["history"].append(f"Aksha: {reply_text}")
        users_col.update_one({"_id": uid}, {"$set": user_doc})

        await msg.reply_text(reply_text)
    except:
        await msg.reply_text("Mood off hai 😏, kal baat krungi")

# ==================================================
# RUN BOT (POLLING)
# ==================================================
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, reply))
    print("🔥 Aksha Bot running with MongoDB + Premium")
    app.run_polling()

if __name__ == "__main__":
    main()
