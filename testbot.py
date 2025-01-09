import os
import telebot
from flask import Flask, request

BOT_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']  # Set in the Vercel environment variables
WEBHOOK_URL = f"https://{os.environ['VERCEL_URL']}/{BOT_TOKEN}"  # Vercel provides the `VERCEL_URL` environment variable

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

@bot.message_handler(commands=['start', 'hello'])
def send_welcome(message):
    bot.reply_to(message, "Hello! How are you doing?")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, message.text)

@app.route(f"/{BOT_TOKEN}", methods=['POST'])
def webhook():
    update = request.get_data().decode("utf-8")
    bot.process_new_updates([telebot.types.Update.de_json(update)])
    return "ok", 200

@app.route("/")
def index():
    return "Telegram Bot is running", 200

if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
