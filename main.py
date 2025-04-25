# main.py (Main script)
import os
import signal
import sys
from dotenv import load_dotenv
from telegram import Bot
from app import app as flask_app

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

def signal_handler(sig, frame):
    print('Exiting gracefully...')
    sys.exit(0)

if __name__ == "__main__":
    # Set up signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Set the webhook when starting
    try:
        bot = Bot(token=BOT_TOKEN)
        print(f"Setting webhook to {WEBHOOK_URL}")
        bot.set_webhook(WEBHOOK_URL)
        print("Webhook set successfully")
    except Exception as e:
        print(f"Failed to set webhook: {e}")
    
    # Start Flask app
    print("Starting Flask server...")
    flask_app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), threaded=True)