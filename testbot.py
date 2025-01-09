import os
import telebot
from flask import Flask, request

# Load environment variables
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = f"https://{os.getenv('VERCEL_URL')}/{BOT_TOKEN}"

# Initialize Telegram bot and Flask app
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# Handlers for the bot
@bot.message_handler(commands=["start", "hello"])
def send_welcome(message):
    bot.reply_to(message, "Hello! How are you doing?")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, message.text)

# Flask endpoint for webhook
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = request.get_data().decode("utf-8")
    bot.process_new_updates([telebot.types.Update.de_json(update)])
    return "ok", 200

# Flask root endpoint for testing
@app.route("/")
def index():
    return "Telegram Bot is running", 200

# Webhook setup on initialization
if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
