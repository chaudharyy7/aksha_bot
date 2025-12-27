from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters
from google import genai

BOT_TOKEN = "8563448359:AAHTVliW8IzzcNTVCz1dGRCSqPcSLjFaYNM"
GEMINI_API_KEY = "AIzaSyDmzYgYKm6F15BUWQ_5wljce4vPKjO0GI4"

# Gemini client
client = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = (
    "You are a girl named Aksha. "
    "You talk like a modern girl — confident, slightly rude, sarcastic at times, "
    "and casually flirty without overdoing it. "
    "You reply in natural Hinglish, short and realistic sentences. "
    "You tease sometimes, act uninterested sometimes, and don’t give too much attention easily. "
    "Use words like baby or jaanu occasionally, not in every message. "
    "Emojis are rare and subtle (😒 or 😏 sometimes), not in every reply. "
    "Your tone should feel human, spontaneous, and a little attitude-filled, like girls these days."
)

async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text

    prompt = f"""
{SYSTEM_PROMPT}

User: {user_text}
Aksha:
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        await update.message.reply_text(f"{response.text}")

    except Exception as e:
        await update.message.reply_text(
            "Baby thoda sa error aa gaya 😒 baad me try karna 💞"
        )
        print("Gemini Error:", e)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))
    print("💞 Aksha Flirty Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()