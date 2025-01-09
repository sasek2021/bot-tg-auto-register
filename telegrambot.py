from fastapi import FastAPI, Request
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler

# Telegram Bot Token
BOT_TOKEN = "7756256878:AAHwv5AvJ0pevOBOhTxupVlGXVYnpfZtUP0"

# Initialize the FastAPI app
app = FastAPI()

# Create the Telegram Bot Application
application = Application.builder().token(BOT_TOKEN).build()

# Define a command handler
async def start(update: Update, context):
    await update.message.reply_text("Hello! I am your bot.")

# Add the command handler to the bot
application.add_handler(CommandHandler("start", start))

@app.post("/")
async def webhook(request: Request):
    """Handle incoming Telegram updates."""
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return {"status": "ok"}

@app.get("/")
async def index():
    return {"message": "Bot is running!"}
