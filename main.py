# main.py
import threading
from app import app as flask_app
from bot import start_bot

def run_flask():
    flask_app.run(host="0.0.0.0", port=5000)

if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

    # Start Telegram bot (blocking)
    start_bot()
