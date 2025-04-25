# main.py (Main script)
import threading
import signal
import sys
from app import app as flask_app
from bot import start_bot

def run_flask():
    flask_app.run(host="0.0.0.0", port=5000, threaded=True)

def signal_handler(sig, frame):
    print('Exiting gracefully...')
    sys.exit(0)

if __name__ == "__main__":
    # Set up signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start Flask in a daemon thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Start Telegram bot (blocking)
    try:
        start_bot()
    except KeyboardInterrupt:
        print("Shutting down...")
        sys.exit(0)