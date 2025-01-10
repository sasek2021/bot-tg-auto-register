from flask import Flask, request
from telegram import Bot

app = Flask(__name__)

@app.route("/", methods=["POST"])
def telegram_webhook():
    bot = Bot(token="7756256878:AAHwv5AvJ0pevOBOhTxupVlGXVYnpfZtUP0")
    update = request.json
    chat_id = update["message"]["chat"]["id"]
    bot.send_message(chat_id, text="Hello from your bot!")
    return "OK"

handler = app
