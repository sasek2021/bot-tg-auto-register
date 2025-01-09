import os
import requests

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7756256878:AAHwv5AvJ0pevOBOhTxupVlGXVYnpfZtUP0")  # Replace with a secure token
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://bot-tg-auto-register.vercel.app/webhook")

def set_webhook():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
    payload = {"url": WEBHOOK_URL}
    response = requests.post(url, json=payload)
    print(f"Webhook set response: {response.json()}")  # For debugging

if __name__ == "__main__":
    set_webhook()
