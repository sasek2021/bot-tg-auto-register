from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters

# Telegram Bot Token
BOT_TOKEN = "7756256878:AAHwv5AvJ0pevOBOhTxupVlGXVYnpfZtUP0"

# Initialize Flask App
app = Flask(__name__)

# Initialize Telegram Bot and Dispatcher
bot = Bot(token=BOT_TOKEN)
dispatcher = Dispatcher(bot, None, workers=0)

# Handlers
def start(update, context):
    update.message.reply_text("Hello! I am your bot.")

def echo(update, context):
    update.message.reply_text(update.message.text)

# Add Handlers to Dispatcher
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))

# Webhook Route
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

# Health Check Route
@app.route("/", methods=["GET"])
def index():
    return "Bot is running!"

if __name__ == "__main__":
    app.run(debug=True)
