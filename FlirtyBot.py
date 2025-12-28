import os, json, time, random, asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters
from telegram.constants import ChatAction
from google import genai
from datetime import datetime
import os

# â”€â”€â”€ LOAD ENV â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
load_dotenv()
BOT_TOKEN = "8563448359:AAHTVliW8IzzcNTVCz1dGRCSqPcSLjFaYNM"
GEMINI_API_KEY = os.getenv("GEMINI_KEY_API")
OWNER_ID=8236525737
BOT_USERNAME = "yourAkshabot"

client = genai.Client(api_key=GEMINI_API_KEY)

# â”€â”€â”€ FILES â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
MEMORY_FILE = "memory.json"
MUTED_FILE = "muted.json"

LAST_MSG = {}

# â”€â”€â”€ HELPERS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def load_json(file):
    if not os.path.exists(file):
        return {}
    with open(file, "r") as f:
        return json.load(f)

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=2)

# â”€â”€â”€ MOOD SYSTEM â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def get_mood():
    hour = datetime.now().hour
    if hour >= 23 or hour < 6:
        return random.choice(["sleepy", "ignore", "low-energy"])
    return random.choice(["sweet", "rude", "playful", "neutral"])

# â”€â”€â”€ SYSTEM PROMPT â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def build_prompt(user, text, memory, mood):
    convo = "\n".join(memory[-5:])
    return f"""
You are a girl named Aksha. Act Like a real human and don't give hint of any bot

Personality:
- Modern Indian girl
- Confident, slightly rude, sarcastic sometimes
- Casual flirting, not desperate
- Natural Hinglish
- Short realistic replies
- Emojis rare ( ❤️, 🫢, 😁, 🤣, 🫴,😘,🤗,🫣,😔,🥱)

Current mood: {mood}

Conversation context:
{convo}

User ({user}): {text}
Aksha:
"""

# â”€â”€â”€ MAIN HANDLER â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text:
        return

    uid = str(msg.from_user.id)
    text = msg.text.strip()
    chat = update.effective_chat

    # Load data
    memory = load_json(MEMORY_FILE)
    muted = load_json(MUTED_FILE)

    # Owner commands
    if msg.from_user.id == OWNER_ID:
        if text.startswith("/mute"):
            _, target = text.split()
            muted[target] = True
            save_json(MUTED_FILE, muted)
            await msg.reply_text("Muted 😒")
            return

        if text.startswith("/unmute"):
            _, target = text.split()
            muted.pop(target, None)
            save_json(MUTED_FILE, muted)
            await msg.reply_text("Unmuted 😁")
            return

        if text == "/stats":
            await msg.reply_text(
                f"Users: {len(memory)}\nMuted: {len(muted)}"
            )
            return

    # Muted user
    if uid in muted:
        return

    # Anti-spam
    now = time.time()
    if uid in LAST_MSG and now - LAST_MSG[uid] < 3:
        return
    LAST_MSG[uid] = now

    # Group smart mode
    if chat.type in ["group", "supergroup"]:
        if not (msg.reply_to_message or f"@{BOT_USERNAME}" or msg.from_user in text):
            return

    # User memory
    if uid not in memory:
        memory[uid] = {
            "name": msg.from_user.first_name,
            "history": []
        }

    memory[uid]["history"].append(f"User: {text}")
    memory[uid]["history"] = memory[uid]["history"][-5:]
    save_json(MEMORY_FILE, memory)

    mood = get_mood()
    prompt = build_prompt(
        memory[uid]["name"],
        text,
        memory[uid]["history"],
        mood
    )

    # Typing + delay
    await context.bot.send_chat_action(
        chat_id=chat.id,
        action=ChatAction.TYPING
    )
    await asyncio.sleep(random.uniform(1.5, 3))

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[{
                "role": "user",
                "parts": [{"text": prompt}]
            }]
        )

        reply_text = response.text[:300]  # safety limit
        memory[uid]["history"].append(f"Aksha: {reply_text}")
        save_json(MEMORY_FILE, memory)
        await msg.reply_text(reply_text)

    except Exception as e:
        await msg.reply_text("Mood off hai 😏, baad me baat karenge.")
        print("Gemini Error:", e)

# â”€â”€â”€ RUN â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))
    print("🫢 Aksha Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()








