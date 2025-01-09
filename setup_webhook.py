import os
import telebot

BOT_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
WEBHOOK_URL = os.environ['WEBHOOK_URL']
bot = telebot.TeleBot(BOT_TOKEN)

# Remove existing webhook
bot.remove_webhook()

# Set new webhook
bot.set_webhook(url=WEBHOOK_URL)
