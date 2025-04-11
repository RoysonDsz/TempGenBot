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

# Virtual Number API setup (NEW one you're using now)
VIRTUAL_NUMBER_API_HOST = "virtual-number.p.rapidapi.com"
VIRTUAL_NUMBER_HEADERS = {
    "x-rapidapi-key": VIRTUAL_NUMBER_API_KEY,
    "x-rapidapi-host": VIRTUAL_NUMBER_API_HOST
}

# Message Cache
message_cache = {}

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

    for _ in range(90):  # Poll for 15 minutes
        url = f"https://{TEMP_MAIL_API_HOST}/api/v3/email/{temp_email}/messages"
        response = requests.get(url, headers=TEMP_MAIL_HEADERS)

        if response.status_code == 200:
            messages = response.json()
            for msg in messages:
                msg_id = msg.get("id")

                if msg_id not in seen_messages:
                    seen_messages.add(msg_id)

                    message_cache[temp_email] = {
                        "from": msg.get("from"),
                        "subject": msg.get("subject"),
                        "body": msg.get("text")
                    }

                    print("📧 New Message Received!")
                    return
        time.sleep(10)

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
            selected_number = phone_data[0]  # it's just a string now!
            return selected_number
        else:
            print("❌ No numbers found.")
            return None
    else:
        print("❌ Error fetching number:", response.text)
        return None



def get_virtual_sms(country_id, phone_number):
    url = "https://virtual-number.p.rapidapi.com/api/v1/e-sim/view-messages"
    querystring = {"countryId": country_id, "number": phone_number}

    response = requests.get(url, headers=VIRTUAL_NUMBER_HEADERS, params=querystring)

    if response.status_code == 200:
        return response.json()
    else:
        print("❌ Failed to get SMS:", response.text)
        return None

# ------------------- FLASK ROUTES ------------------- #
@app.route('/generate/email', methods=['GET'])
def generate_email():
    temp_email = generate_temp_email()
    if not temp_email:
        return jsonify({"error": "Failed to create temporary email"}), 500

    threading.Thread(target=poll_inbox, args=(temp_email,)).start()
    return jsonify({"temp_email": temp_email})


@app.route('/generate/number', methods=['GET'])
def generate_number():
    country_id = request.args.get('country_id', '7')  # Default Russia
    number = generate_virtual_phone_number(country_id)
    if number:
        return jsonify({
            "virtual_phone": number,
            "country_id": country_id
        })
    else:
        return jsonify({"error": "Could not generate virtual phone number"}), 500



@app.route('/poll_sms/<int:country_id>/<phone_number>', methods=['GET'])
def poll_sms(country_id, phone_number):
    # Wait 2 minutes (120 seconds)
    time.sleep(120)

    # Now make a single request to check for SMS
    response = requests.get(
        "https://virtual-number.p.rapidapi.com/api/v1/e-sim/view-messages",
        headers=VIRTUAL_NUMBER_HEADERS,
        params={"countryId": str(country_id), "number": phone_number}
    )

    if response.status_code == 200:
        messages = response.json()
        print(messages)
        if messages:
            return jsonify(messages)

    # If no messages found after 2 minutes
    return jsonify({"message": "No SMS received yet."}), 204



# ------------------- RUNNING THE SERVER ------------------- #
if __name__ == '__main__':
    app.run(port=5000)
