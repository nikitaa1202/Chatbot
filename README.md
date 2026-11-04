# WhatsApp Student Chatbot

A Flask chatbot that lets students check their academic and fee details over WhatsApp. Student records are read from Google Sheets, and access is protected by an OTP sent through the Twilio WhatsApp API.

## Features
- Multi-step conversation: class (FE, SE, TE, BE), branch (AIML, COMP, CIVIL, MECH, CHEM, EXTC), roll number, OTP, then a menu
- Average attendance and subject-wise attendance
- Pending fees and mess bill
- OTP verification sent to the registered phone numbers before any data is shown
- "exit" can be typed at any step to end the conversation

## Tech Stack
Python, Flask, Twilio WhatsApp API, Google Sheets API

## How It Works
Twilio sends each incoming WhatsApp message to the `/whatsapp` route. The bot tracks the conversation step in a Flask session, reads the matching row from the Google Sheet for the chosen class and branch, and replies with a Twilio `MessagingResponse`.

## Setup
1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
2. Create a free Twilio account and use the Twilio WhatsApp sandbox to test the bot.
3. Create a Google Cloud service account, enable the Google Sheets API, download its JSON key and save it as `credentials.json`. Share each student Google Sheet with the service account's email.
4. Copy `.env.example` to `.env` and fill in your own values:
   - `FLASK_SECRET_KEY`
   - `GOOGLE_CREDENTIALS_PATH`
   - `TWILIO_ACCOUNT_SID`
   - `TWILIO_AUTH_TOKEN`
   - `TWILIO_PHONE_NUMBER`
5. Replace the Google Sheet IDs in `SHEET_IDS` in `bot.py` with your own sheets.
6. Run the app:
   ```
   flask --app bot run
   ```
7. Expose it to Twilio (for example with ngrok) and set the Twilio WhatsApp sandbox webhook to `https://<your-url>/whatsapp`.

## Notes
- Never commit `.env` or `credentials.json`. Both are listed in `.gitignore`.
- OTPs and verified sessions are stored in memory, so they reset when the server restarts.

## My Role
[Write 2-3 lines here: what you built, and which part a teammate worked on.]
