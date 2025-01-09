from fastapi import FastAPI, Request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler
import os


# Telegram Bot Token
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')


# Initialize the FastAPI app
app = FastAPI()

# Initialize the Telegram Bot
bot = Bot(token=BOT_TOKEN)

# Dispatcher to handle Telegram updates
dispatcher = Dispatcher(bot, None, workers=0)

# Define a simple command
def start(update, context):
    update.message.reply_text("Hello! I am your bot.")

# Add command handlers to the dispatcher
dispatcher.add_handler(CommandHandler("start", start))

@app.post("/")
async def webhook(request: Request):
    """Handle incoming Telegram updates."""
    data = await request.json()
    update = Update.de_json(data, bot)
    dispatcher.process_update(update)
    return {"status": "ok"}

@app.get("/")
async def index():
    return {"message": "Bot is running!"}
