# bot.py (Telegram Bot)
import os
import requests
import time
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove 
from telegram.ext import (
    CommandHandler, MessageHandler, Filters, CallbackContext,
    ConversationHandler, Dispatcher
)

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Define API base URL - use an environment variable to allow different deployment locations
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:5000")

# Define states for conversation
WAITING_FOR_COUNTRY = 1

# Dictionary to store active sessions
active_sessions = {}

# ───────────────────────────────────────────── #
# Start & Help
# ───────────────────────────────────────────── #
def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "👋 Welcome to *TempGen Bot*!\n\n"
        "Use the commands below:\n"
        "• /generate_email - Get a temp email\n"
        "• /generate_phone - Get a temp phone number\n"
        "• /cancel - Cancel current operation\n"
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
        # Cancel any existing operation
        user_id = update.effective_user.id
        if user_id in active_sessions:
            session_id = active_sessions[user_id].get('email')
            if session_id:
                requests.post(f"{API_BASE_URL}/cancel/{session_id}")
        
        # Inform user
        status_message = update.message.reply_text("🔍 Generating temporary email...")
        
        # Request new email
        response = requests.get(f"{API_BASE_URL}/generate/email")
        if response.status_code != 200:
            update.message.reply_text("❌ Could not generate email.")
            return

        temp_email = response.json().get("temp_email")
        if not temp_email:
            update.message.reply_text("❌ Email generation failed.")
            return
            
        # Store the email in active sessions
        active_sessions[user_id] = {'email': temp_email, 'type': 'email'}
        
        # Update status message
        status_message.edit_text(
            f"📧 Temporary Email created: `{temp_email}`\n\n"
            "Waiting for incoming messages (15 mins max)...\n"
            "Use /cancel to stop waiting.",
            parse_mode='Markdown'
        )

        # Poll for messages
        for attempt in range(90):  # 15 minutes (90 * 10s)
            message_response = requests.get(f"{API_BASE_URL}/get_messages/{temp_email}")
            
            if message_response.status_code == 200:
                msg_data = message_response.json()
                print(msg_data)
                
                if msg_data.get("status") == "received":
                    update.message.reply_text(
                        f"💌 New Message Received!\n\n"
                        f"From: {msg_data['from']}\n"
                        f"Subject: {msg_data['subject']}\n\n"
                        f"{msg_data['body']}"
                    )
                    # Clear session
                    if user_id in active_sessions:
                        del active_sessions[user_id]
                    return
                elif msg_data.get("status") == "timeout":
                    update.message.reply_text("📭 No new messages arrived in 15 minutes. Try again later.")
                    # Clear session
                    if user_id in active_sessions:
                        del active_sessions[user_id]
                    return
                elif msg_data.get("status") == "error":
                    update.message.reply_text(f"⚠️ Error: {msg_data.get('message', 'Unknown error')}")
                    # Clear session
                    if user_id in active_sessions:
                        del active_sessions[user_id]
                    return
                elif msg_data.get("status") == "cancelled":
                    # Already handled by cancel function
                    return
            
            # Check if user has cancelled
            if user_id not in active_sessions or active_sessions[user_id].get('email') != temp_email:
                return
                
            time.sleep(10)

        # If we get here, timeout occurred
        update.message.reply_text("📭 No new messages arrived in 15 minutes. Try again later.")
        # Clear session
        if user_id in active_sessions:
            del active_sessions[user_id]

    except Exception as e:
        update.message.reply_text(f"⚠️ Error: {e}")
        # Clear session
        if user_id in active_sessions:
            del active_sessions[user_id]

# ───────────────────────────────────────────── #
# Generate Phone Number (Conversation)
# ───────────────────────────────────────────── #
def generate_phone_start(update: Update, context: CallbackContext):
    keyboard = [['7 - Russia', '91 - India'], ['380 - Ukraine', '55 - Brazil'], ['Cancel']]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    update.message.reply_text(
        "📍 Please select a country or enter a country code:",
        reply_markup=reply_markup
    )
    return WAITING_FOR_COUNTRY

def receive_country_code(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    
    # Extract the country code from input (handles both formats like "7 - Russia" and "7")
    country_text = update.message.text.strip()
    if " - " in country_text:
        country_code = country_text.split(" - ")[0].strip()
    else:
        country_code = country_text
    
    # Validate it's a number
    if not country_code.isdigit():
        update.message.reply_text(
            "⚠️ Please enter a valid country code (numbers only).",
            reply_markup=ReplyKeyboardRemove()
        )
        return WAITING_FOR_COUNTRY
    
    # Cancel any existing operation for this user
    if user_id in active_sessions:
        session_id = active_sessions[user_id].get('sms_session')
        if session_id:
            requests.post(f"{API_BASE_URL}/cancel/{session_id}")
    
    # Generate number
    status_message = update.message.reply_text(
        f"🔍 Generating temporary phone number for country code {country_code}...",
        reply_markup=ReplyKeyboardRemove()
    )
    
    response = requests.get(f"{API_BASE_URL}/generate/number?country_id={country_code}")

    if response.status_code == 200:
        data = response.json()
        temp_number = data.get("virtual_phone", "Number not found")
        session_id = data.get("session_id")
        
        # Store the session ID
        active_sessions[user_id] = {'sms_session': session_id, 'type': 'sms'}
        
        try:
            update.message.reply_text(
                f"📱 Temporary Phone Number:\n`{temp_number}`\n\n"
                "Waiting for incoming SMS... ⏳\n"
                "Use /cancel to stop waiting.",
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"Failed to edit message: {e}")

        # Poll for SMS
        for attempt in range(30):  # 5 minutes (30 * 10s)
            sms_response = requests.get(f"{API_BASE_URL}/check_sms/{session_id}")
            
            if sms_response.status_code == 200:
                sms_data = sms_response.json()
                
                if sms_data.get("status") == "received":
                    messages = sms_data.get("messages", [])
                    
                    if messages:
                        # Format the first message
                        msg = messages[0]
                        update.message.reply_text(
                            f"📩 New SMS Received!\n\n"
                            f"From: {msg.get('from', 'Unknown')}\n"
                            f"Message: {msg.get('message', 'No content')}\n"
                            f"Time: {msg.get('time', 'Unknown')}"
                        )
                        
                        # Handle additional messages if present
                        if len(messages) > 1:
                            update.message.reply_text(f"➕ {len(messages)-1} more messages received.")
                        
                        # Clear session
                        if user_id in active_sessions:
                            del active_sessions[user_id]
                        return ConversationHandler.END
                elif sms_data.get("status") == "timeout":
                    update.message.reply_text("📭 No SMS received in 5 minutes. Try again later.")
                    # Clear session
                    if user_id in active_sessions:
                        del active_sessions[user_id]
                    return ConversationHandler.END
                elif sms_data.get("status") == "error":
                    update.message.reply_text(f"⚠️ Error: {sms_data.get('message', 'Unknown error')}")
                    # Clear session
                    if user_id in active_sessions:
                        del active_sessions[user_id]
                    return ConversationHandler.END
                elif sms_data.get("status") == "cancelled":
                    # Already handled by cancel function
                    return ConversationHandler.END
            
            # Check if user has cancelled
            if user_id not in active_sessions or active_sessions[user_id].get('sms_session') != session_id:
                return ConversationHandler.END
                
            time.sleep(10)

        # If we get here, timeout occurred
        update.message.reply_text("📭 No SMS received in 5 minutes. Try again later.")
        # Clear session
        if user_id in active_sessions:
            del active_sessions[user_id]
    else:
        update.message.reply_text(
            f"❌ Failed to generate number.\nAPI Response: {response.text}",
            reply_markup=ReplyKeyboardRemove()
        )

    return ConversationHandler.END

def cancel_command(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    
    if user_id not in active_sessions:
        update.message.reply_text("❓ No active operation to cancel.")
        return ConversationHandler.END
    
    session_info = active_sessions[user_id]
    
    if session_info.get('type') == 'email':
        email = session_info.get('email')
        if email:
            # Cancel on server
            requests.post(f"{API_BASE_URL}/cancel/{email}")
            update.message.reply_text("✅ Email monitoring cancelled.")
    elif session_info.get('type') == 'sms':
        session_id = session_info.get('sms_session')
        if session_id:
            # Cancel on server
            requests.post(f"{API_BASE_URL}/cancel/{session_id}")
            update.message.reply_text("✅ SMS monitoring cancelled.")
    
    # Clear the session
    del active_sessions[user_id]
    return ConversationHandler.END

def cancel_conversation(update: Update, context: CallbackContext):
    update.message.reply_text(
        "❌ Operation cancelled.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

def error_handler(update, context):
    """Log errors caused by Updates."""
    print(f"Error occurred: {context.error}")

# Process webhook updates
def process_update(update_json, bot):
    """Process incoming webhook update."""
    update = Update.de_json(update_json, bot)
    dispatcher = Dispatcher(bot, None, workers=0, use_context=True)
    
    # Register handlers
    dispatcher.add_error_handler(error_handler)
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("generate_email", generate_email))
    dispatcher.add_handler(CommandHandler("cancel", cancel_command))

    phone_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("generate_phone", generate_phone_start)],
        states={
            WAITING_FOR_COUNTRY: [
                MessageHandler(Filters.regex('^Cancel$'), cancel_conversation),
                MessageHandler(Filters.text & ~Filters.command, receive_country_code)
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)]
    )
    dispatcher.add_handler(phone_conv_handler)

    # Process the update
    dispatcher.process_update(update)