import os
import requests
from dotenv import load_dotenv
import time
from telegram import Update
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters,
    CallbackContext, ConversationHandler
)

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Define states for conversation
WAITING_FOR_COUNTRY = 1

# ───────────────────────────────────────────── #
# Start & Help
# ───────────────────────────────────────────── #
def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "👋 Welcome to *TempGen Bot*!\n\n"
        "Use the commands below:\n"
        "• /generate_email - Get a temp email\n"
        "• /generate_phone - Get a temp phone number\n"
        "• /help - Show this menu again",
        parse_mode='Markdown'
    )

def help_command(update: Update, context: CallbackContext):
    start(update, context)

# ───────────────────────────────────────────── #
# Generate Email
# ───────────────────────────────────────────── #

def generate_email(update: Update, context: CallbackContext):
    try:
        response = requests.get("http://127.0.0.1:5000/generate/email")
        if response.status_code != 200:
            update.message.reply_text("❌ Could not generate email.")
            return

        temp_email = response.json().get("temp_email")
        update.message.reply_text(f"📧 Temporary Email created: {temp_email}\n\nWaiting for incoming messages (2 mins max)...")

        # Poll every 10 seconds, up to 2 minutes
        for _ in range(90):  # 90 x 10s = 1000s = 15 mins
            message_response = requests.get(f"http://127.0.0.1:5000/get_messages/{temp_email}")
            if message_response.status_code == 200:
                msg = message_response.json()
                update.message.reply_text(
                    f"💌 New Message Received!\nFrom: {msg['from']}\nSubject: {msg['subject']}\n\n{msg['body']}"
                )
                return
            time.sleep(10)

        update.message.reply_text("📭 No new messages arrived in 15 minutes. Try again later.")

    except Exception as e:
        update.message.reply_text(f"⚠️ Error: {e}")


# ───────────────────────────────────────────── #
# Generate Phone Number (Conversation)
# ───────────────────────────────────────────── #
def generate_phone_start(update: Update, context: CallbackContext):
    update.message.reply_text("📍 Please enter the country code (like `7` for Russia or `91` for India):")
    return WAITING_FOR_COUNTRY

def receive_country_code(update: Update, context: CallbackContext):
    country_code = update.message.text.strip()
    response = requests.get(f"http://127.0.0.1:5000/generate/number?country_id={country_code}")

    if response.status_code == 200:
        data = response.json()
        temp_number = data.get("virtual_phone", "Number not found")
        update.message.reply_text(
            f"📱 Temporary Phone Number (Country {country_code}): {temp_number}\n\nWaiting for incoming SMS... ⏳"
        )

        # Poll for up to 15 minutes (every 10s = 90 times)
        for attempt in range(90):
            sms_response = requests.get(f"http://127.0.0.1:5000/poll_sms/{country_code}/{temp_number}")
            
            if sms_response.status_code == 200:
                sms_list = sms_response.json()

                if isinstance(sms_list, list) and sms_list:
                    # Grab the first SMS in the list
                    msg = sms_list[0]
                    update.message.reply_text(
                        f"📩 New SMS Received!\nFrom: {msg['from']}\nMessage: {msg['message']}\nTime: {msg['time']}"
                    )
                    return ConversationHandler.END

            time.sleep(10)

        update.message.reply_text("📭 No SMS received in 15 minutes. Try again later.")
    else:
        update.message.reply_text(f"❌ Failed to generate number.\nAPI Response: {response.content}")

    return ConversationHandler.END



def cancel(update: Update, context: CallbackContext):
    update.message.reply_text("❌ Phone generation cancelled.")
    return ConversationHandler.END

# ───────────────────────────────────────────── #
# Main
# ───────────────────────────────────────────── #
def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    # Command Handlers
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(CommandHandler("generate_email", generate_email))

    # Conversation Handler for Phone Number
    phone_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("generate_phone", generate_phone_start)],
        states={
            WAITING_FOR_COUNTRY: [MessageHandler(Filters.text & ~Filters.command, receive_country_code)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    dp.add_handler(phone_conv_handler)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
