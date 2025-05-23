# 🤖 TempGenBot

**TempGenBot** is a Telegram bot that helps you generate **temporary phone numbers and email addresses** on the fly. Perfect for receiving OTPs, testing services, or signing up anonymously — without giving up your real info.

Built using **Flask** and **Telegram Bot API**, with integration to virtual number/email services via **RapidAPI**.

---

## 🚀 Features

- 📱 Generate temporary **phone numbers** for any supported country
- 📩 Poll for incoming **SMS messages (OTP, codes, etc.)**
- 📧 Create disposable **email addresses** and retrieve inbox messages
- 🔐 Basic **role-based access control** for admin/user functionality
- ⚙️ Fully modular backend using Flask + REST API
- 🤖 Seamless Telegram bot integration

---

## 🧰 Tech Stack

- **Backend**: Python, Flask
- **Telegram Bot**: python-telegram-bot
- **External APIs**: RapidAPI (for virtual phone/email services)
- **Polling & Response**: `requests`, `time`, `json`

---

## 📦 Installation & Setup

### 1. Clone this repo

```bash
git clone https://github.com/RoysonDsz/TempGenBot.git
