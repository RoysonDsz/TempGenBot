# app.py (Flask Server)
from flask import Flask, jsonify, request
import requests
import time
import threading
import os
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

# Load environment variables
TEMP_MAIL_API_KEY = os.getenv("TEMP_MAIL_API_KEY")
VIRTUAL_NUMBER_API_KEY = os.getenv("VIRTUAL_NUMBER_API_KEY")

# Temp-Mail API setup
TEMP_MAIL_API_HOST = "temp-mail44.p.rapidapi.com"
TEMP_MAIL_HEADERS = {
    "x-rapidapi-key": TEMP_MAIL_API_KEY,
    "x-rapidapi-host": TEMP_MAIL_API_HOST,
    "Content-Type": "application/json"
}

# Virtual Number API setup
VIRTUAL_NUMBER_API_HOST = "virtual-number.p.rapidapi.com"
VIRTUAL_NUMBER_HEADERS = {
    "x-rapidapi-key": VIRTUAL_NUMBER_API_KEY,
    "x-rapidapi-host": VIRTUAL_NUMBER_API_HOST
}

# Message Cache
message_cache = {}
operation_status = {}

# ------------------- TEMP EMAIL STUFF ------------------- #
def generate_temp_email():
    url = f"https://{TEMP_MAIL_API_HOST}/api/v3/email/new"
    response = requests.post(url, headers=TEMP_MAIL_HEADERS)

    if response.status_code == 200:
        email_data = response.json()
        temp_email = email_data.get("email")
        print(f"✅ Temporary Email Created: {temp_email}")
        return temp_email
    else:
        print("❌ Failed to create email:", response.text)
        return None

def poll_inbox(temp_email):
    seen_messages = set()
    
    try:
        # Initialize status as "waiting"
        operation_status[temp_email] = "waiting"
        
        for _ in range(90):  # Poll for 15 minutes (90 * 10s = 900s = 15min)
            # Check if operation has been cancelled
            if operation_status.get(temp_email) == "cancelled":
                print(f"📧 Polling cancelled for {temp_email}")
                return
            
            url = f"https://{TEMP_MAIL_API_HOST}/api/v3/email/{temp_email}/messages"
            response = requests.get(url, headers=TEMP_MAIL_HEADERS)

            if response.status_code == 200:
                messages = response.json()
                print(messages)
                for msg in messages:
                    msg_id = msg.get("id")

                    if msg_id not in seen_messages:
                        seen_messages.add(msg_id)

                        message_cache[temp_email] = {
                            "status": "received",
                            "from": msg.get("from"),
                            "subject": msg.get("subject"),
                            "body": msg.get("body_text") or msg.get("body_html") or "No content" 
                        }

                        operation_status[temp_email] = "complete"
                        print("📧 New Message Received!")
                        return
            time.sleep(10)
        
        # If no messages after 15 minutes
        message_cache[temp_email] = {
            "status": "timeout",
            "message": "No messages received after 15 minutes"
        }
        operation_status[temp_email] = "timeout"
    except Exception as e:
        print(f"Error while polling inbox: {e}")
        message_cache[temp_email] = {
            "status": "error",
            "message": str(e)
        }
        operation_status[temp_email] = "error"

# ------------------- VIRTUAL NUMBER STUFF ------------------- #
def generate_virtual_phone_number(country_id):
    url = "https://virtual-number.p.rapidapi.com/api/v1/e-sim/country-numbers"
    querystring = {"countryId": country_id}

    response = requests.get(url, headers=VIRTUAL_NUMBER_HEADERS, params=querystring)
    print("📲 Number Fetch Status Code:", response.status_code)
    print("📲 API Response:", response.text)

    if response.status_code == 200:
        phone_data = response.json()

        if isinstance(phone_data, list) and phone_data:
            selected_number = phone_data[0]  # Just get first number
            return selected_number
        else:
            print("❌ No numbers found.")
            return None
    else:
        print("❌ Error fetching number:", response.text)
        return None

def poll_sms_background(country_id, phone_number, session_id):
    try:
        operation_status[session_id] = "waiting"
        
        # Poll for up to 5 minutes (30 * 10s = 300s = 5min)
        for _ in range(30):
            # Check if operation has been cancelled
            if operation_status.get(session_id) == "cancelled":
                print(f"📱 SMS polling cancelled for {phone_number}")
                return
            
            url = "https://virtual-number.p.rapidapi.com/api/v1/e-sim/view-messages"
            querystring = {"countryId": str(country_id), "number": phone_number}
            
            response = requests.get(url, headers=VIRTUAL_NUMBER_HEADERS, params=querystring)
            
            if response.status_code == 200:
                messages = response.json()
                if messages and isinstance(messages, list) and len(messages) > 0:
                    message_cache[session_id] = {
                        "status": "received",
                        "messages": messages
                    }
                    operation_status[session_id] = "complete"
                    print(f"📱 SMS received for {phone_number}")
                    return
            
            time.sleep(10)
        
        # If no SMS after timeout
        message_cache[session_id] = {
            "status": "timeout",
            "message": "No SMS received after 5 minutes"
        }
        operation_status[session_id] = "timeout"
    except Exception as e:
        print(f"Error while polling SMS: {e}")
        message_cache[session_id] = {
            "status": "error",
            "message": str(e)
        }
        operation_status[session_id] = "error"

# ------------------- FLASK ROUTES ------------------- #
@app.route('/generate/email', methods=['GET'])
def generate_email():
    temp_email = generate_temp_email()
    if not temp_email:
        return jsonify({"error": "Failed to create temporary email"}), 500

    # Initialize the cache entry
    message_cache[temp_email] = {"status": "pending", "message": "Waiting for emails..."}
    
    # Start polling in a separate thread
    threading.Thread(target=poll_inbox, args=(temp_email,), daemon=True).start()
    return jsonify({"temp_email": temp_email})

@app.route('/get_messages/<temp_email>', methods=['GET'])
def get_messages(temp_email):
    
    if temp_email in message_cache:
        return jsonify(message_cache[temp_email])
    else:
        return jsonify({"error": "Email not found"}), 404

@app.route('/generate/number', methods=['GET'])
def generate_number():
    country_id = request.args.get('country_id', '7')  # Default Russia
    number = generate_virtual_phone_number(country_id)
    if number:
        # Create a unique session ID for this request
        session_id = f"sms_{country_id}_{number}_{int(time.time())}"
        
        # Initialize cache for this session
        message_cache[session_id] = {"status": "pending", "message": "Waiting for SMS..."}
        
        # Start polling in a separate thread
        threading.Thread(target=poll_sms_background, 
                         args=(country_id, number, session_id), 
                         daemon=True).start()
        
        return jsonify({
            "virtual_phone": number,
            "country_id": country_id,
            "session_id": session_id
        })
    else:
        return jsonify({"error": "Could not generate virtual phone number"}), 500

@app.route('/check_sms/<session_id>', methods=['GET'])
def check_sms(session_id):
    if session_id in message_cache:
        return jsonify(message_cache[session_id])
    else:
        return jsonify({"error": "Session not found"}), 404

@app.route('/cancel/<operation_id>', methods=['POST'])
def cancel_operation(operation_id):
    if operation_id in operation_status:
        operation_status[operation_id] = "cancelled"
        message_cache[operation_id] = {
            "status": "cancelled",
            "message": "Operation was cancelled by user"
        }
        return jsonify({"status": "cancelled"})
    return jsonify({"error": "Operation not found"}), 404

# ------------------- RUNNING THE SERVER ------------------- #
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, threaded=True)
