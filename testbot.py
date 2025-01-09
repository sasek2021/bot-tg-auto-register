import os
from flask import Flask, request
import telebot

app = Flask(__name__)

BOT_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
bot = telebot.TeleBot(BOT_TOKEN)

@app.route('/webhook', methods=['POST'])
def webhook():
    json_str = request.get_data().decode('UTF-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return 'OK', 200

@app.route('/')
def index():
    return 'Bot is up and running!'

if __name__ == '__main__':
    bot.remove_webhook()  # Remove any existing webhook
    bot.set_webhook(url="https://bot-tg-auto-register.vercel.app/webhook")  # Replace with your Vercel URL
    app.run(debug=True)
