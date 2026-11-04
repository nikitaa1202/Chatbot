import os
from dotenv import load_dotenv
from flask import Flask, request, session
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
import random
import logging
from datetime import datetime, timedelta

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')  # Set a secret key for session management

# Google Sheets credentials and settings
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# Updated Google Sheet IDs for different classes and branches (including EXTC)
SHEET_IDS = {
    'fe': {
        'aiml': '11bFf4s1ilW5Jg3gbgWByfbLM1umt0pZncdB3zBdomkg',
        'comp': '1Yt0_xXw2Mogq2Cg8YBkuglSvLyXtAHxb134-4j7oS2U',
        'civil': '1CCxTZ7RH6xXtwohCnIzSZzQf0NFPnF_xbRL_TRMIYbA',
        'mech': '1qnKrfHxQNjOqXU04j9tkCFcj1ZVymS6vX6WJ_KHv_24',
        'chem': '1idb8fi0xxOROxZO5wwu89ztIDrQRlClADKaO7gD6XXA',
        'extc': '1dwWzGvlDm80_cOBvK7sQySfH0Syh8o0EYdYUASE-_AY'
    },
    'se': {
        'aiml': '1p1U_Xi7-jV0vE6n4njZWlTgTznSDuUrB3bx7QbSpysE',
        'comp': '13icrARu1zl7-AzsWHgxZwWXHYMpGvCV6UTNQIAz1GPE',
        'civil': '1_tNokB6eJxr6GqQEvhR46HuOT1fg9KGGY-ESvQZFKeQ',
        'mech': '1m-0hPbxKcHu5_vQxCpyhzxZRzdt5SCgI-cpXkEfStUk',
        'chem': '1v1bL_W8Min01HZ19e9whrOvh20BB8CHLLA82Z117q8o',
        'extc': '1HBDmnhzyFh8QNB6XOHT2MXqcZNyBB-lg94Vw0aIuKEE'
    },
    'te': {
        'aiml': '1coPrHSQO7YwLgEE0af64jZyKBmGNcNzvtzyMODwkMQ0',
        'comp': '1oedxFcqueSdUSMzJrvXViJnGym0tjpoFznWKVOwi4Zw',
        'civil': '15CVKNvz27pMja20fzgfQ6pGCWQoSDnzw3927NdsHvkI',
        'mech': '1wQt2FkeyGTcIDli3L3wWNz8QfwwyvS_CznvSW6TqDNA',
        'chem': '1JKraAyhU_Xg-GJXIj_dt_Di7VKtGOjZRLxb_WHGgsfM',
        'extc': '1XQJxkKQzLBTLXKkkJjyx5PC-LZqai6sxR-gfq3co_So'
    },
    'be': {
        'aiml': '1EXAMPLEIDforBEAIML',
        'comp': '1Egr2KRRJs9LgMwWrdwnJeuk1VVltGDe0hyAnc50FpJM',
        'civil': '1wzWptEkDzI23d0XOoKBmV2QK57pWBV8XzxphX1AI9UY',
        'mech': '1wPLIzDGGqy1smV46VXwOasadSxdEBpFd-c_Zm5E4r34',
        'chem': '14nOE-ISm14Cs2dYeAqNXRMcuTBUMMtl3d8GKBauMf-g',
        'extc': '1YJ7Nk4ISTUbRf082fExUfieEm8AdAu_d4qeyj6X8QY0'
    }
}

RANGE_NAME = 'Sheet1'

credentials = Credentials.from_service_account_file(
    os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials.json'), scopes=SCOPES)
service = build('sheets', 'v4', credentials=credentials)

# Twilio configuration
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

logging.basicConfig(level=logging.DEBUG)

class AttendanceApp:
    def __init__(self):
        self.otp_store = {}
        self.verified_sessions = {}

    def get_sheet_values(self, class_type, branch_type):
        try:
            spreadsheet_id = SHEET_IDS.get(class_type, {}).get(branch_type)
            if not spreadsheet_id:
                raise ValueError(f"Unknown class or branch type: {class_type} {branch_type}")

            result = service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=RANGE_NAME
            ).execute()
            return result.get('values', [])
        except Exception as e:
            logging.error(f"Error fetching sheet values: {e}")
            return []

    def get_roll_number_row(self, values, roll_number):
        for i, row in enumerate(values):
            if str(row[0]) == str(roll_number):
                return i
        return None

    def get_phone_numbers(self, roll_number, class_type, branch_type):
        values = self.get_sheet_values(class_type, branch_type)
        row_index = self.get_roll_number_row(values, roll_number)
        if row_index is None:
            logging.error(f"Roll number {roll_number} not found.")
            return None, None

        # Adjusted index for phone numbers based on selected branch
        if class_type == 'se':
            primary_phone_index = 9  # J column
            secondary_phone_index = 10  # K column
        else:
            primary_phone_index = 8  # I column
            secondary_phone_index = 9  # J column

        primary_phone = str(values[row_index][primary_phone_index]).strip()
        secondary_phone = str(values[row_index][secondary_phone_index]).strip()

        if not primary_phone.startswith('+'):
            primary_phone = '+91' + primary_phone
        if not secondary_phone.startswith('+'):
            secondary_phone = '+91' + secondary_phone

        return primary_phone, secondary_phone

    def generate_otp(self):
        return random.randint(100000, 999999)

    def send_otp_via_whatsapp(self, primary_phone_number, secondary_phone_number, otp):
        message = f"Your OTP is {otp}. Please enter this code to proceed."
        success_primary, success_secondary = False, False

        # Send OTP to the primary phone number
        try:
            logging.debug(f"Sending OTP to primary number: {primary_phone_number}")
            twilio_client.messages.create(
                body=message,
                from_=TWILIO_PHONE_NUMBER,
                to=f'whatsapp:{primary_phone_number}'
            )
            logging.info(f"OTP sent successfully to primary number: {primary_phone_number}")
            success_primary = True
        except Exception as e:
            logging.error(f"Error sending OTP to primary number {primary_phone_number}: {e}")

        # Send OTP to the secondary phone number
        if secondary_phone_number:
            try:
                logging.debug(f"Sending OTP to secondary number: {secondary_phone_number}")
                twilio_client.messages.create(
                    body=message,
                    from_=TWILIO_PHONE_NUMBER,
                    to=f'whatsapp:{secondary_phone_number}'
                )
                logging.info(f"OTP sent successfully to secondary number: {secondary_phone_number}")
                success_secondary = True
            except Exception as e:
                logging.error(f"Error sending OTP to secondary number {secondary_phone_number}: {e}")

        return success_primary or success_secondary  # Return True if either message was sent successfully

    def store_otp(self, roll_number, otp, sheet_type):
        expiration_time = datetime.now() + timedelta(hours=72)  # OTP valid for 72 hours
        self.otp_store[(roll_number, sheet_type)] = {'otp': otp, 'expires_at': expiration_time}

    def get_stored_otp(self, roll_number, sheet_type):
        otp_info = self.otp_store.get((roll_number, sheet_type))
        if otp_info:
            if datetime.now() < otp_info['expires_at']:
                return otp_info['otp']
        return None

    def verify_otp(self, roll_number, sheet_type, otp):
        stored_otp = self.get_stored_otp(roll_number, sheet_type)
        if stored_otp and str(stored_otp) == str(otp):
            self.verified_sessions[roll_number] = sheet_type
            return True
        return False

    def get_average_attendance(self, roll_number, class_type, branch_type):
        values = self.get_sheet_values(class_type, branch_type)
        row_index = self.get_roll_number_row(values, roll_number)
        if row_index is None:
            logging.error(f"Roll number {roll_number} not found.")
            return None

        # Adjusted index for attendance based on class type
        if class_type == 'se':
            attendance_index = 8  # I column
        else:
            attendance_index = 7  # H column

        return values[row_index][attendance_index]

    def get_pending_fees(self, roll_number, class_type, branch_type):
        values = self.get_sheet_values(class_type, branch_type)
        row_index = self.get_roll_number_row(values, roll_number)
        if row_index is None:
            logging.error(f"Roll number {roll_number} not found.")
            return None

        # Adjusted index for pending fees based on class type
        if class_type == 'se':
            fees_index = 11  # L column
        else:
            fees_index = 10  # K column

        return values[row_index][fees_index]

    def get_mess_bill(self, roll_number, class_type, branch_type):
        values = self.get_sheet_values(class_type, branch_type)
        row_index = self.get_roll_number_row(values, roll_number)
        if row_index is None:
            logging.error(f"Roll number {roll_number} not found.")
            return None

        # Adjusted index for mess bill based on class type
        if class_type == 'se':
            mess_index = 12  # M column
        else:
            mess_index = 11  # L column

        return values[row_index][mess_index]


    def get_subject_attendance(self, roll_number, class_type, branch_type, subject):
        values = self.get_sheet_values(class_type, branch_type)
        row_index = self.get_roll_number_row(values, roll_number)
        if row_index is None:
            logging.error(f"Roll number {roll_number} not found.")
            return None

        # Define the column indexes for each subject in TE(AIML)
        subject_columns = {
            'cn': 2,  # CN attendance in column C
            'wc': 3,  # WC attendance in column D
            'ai': 4,  # AI attendance in column E
            'dwm': 5,  # DWM attendance in column F
            'saids': 6  # SAIDS attendance in column G
        }

        # Get the corresponding column for the selected subject
        subject_column = subject_columns.get(subject.lower())
        if subject_column is None:
            logging.error(f"Invalid subject: {subject}")
            return None

        return values[row_index][subject_column]

attendance_app = AttendanceApp()

@app.route('/whatsapp', methods=['POST'])
def whatsapp_reply():
    incoming_msg = request.form.get('Body').strip().lower()
    sender = request.form.get('From')

    response = MessagingResponse()

    # Initialize session for the sender if not already done
    if 'step' not in session:
        session['step'] = None
        session['sender'] = sender  # Store sender information in the session

    # Initialize verified roll numbers list if not already in session
    if 'verified_roll_numbers' not in session:
        session['verified_roll_numbers'] = []

    # Reset the session if a greeting is detected and check if the user is verified
    if incoming_msg in ['hi', 'hey', 'hello']:
        if session['verified_roll_numbers']:
            # If the user has verified before, show them the options directly
            response.message("Welcome back! Please select an option: \n1. Average Attendance \n2. Subject Attendance \n3. Pending Fees \n4. Mess Bill \nType 'exit' to exit.")
            session['step'] = 'option_selection'
        else:
            # Clear the session and start the process from the beginning
            session.clear()
            session['sender'] = sender  # Keep the sender in the session
            response.message(f"Hey {sender}! Please select a class: \n1. FE \n2. SE \n3. TE \n4. BE \nType 'exit' at any point to exit.")
            session['step'] = 'class_selection'  # Move to class selection
        return str(response)

    # Exit at any point
    if incoming_msg == 'exit':
        response.message("You have exited the conversation. Thank you!")
        session.clear()  # Clear the session to end the interaction
        return str(response)

    # Class selection step
    if session.get('step') == 'class_selection':
        class_choice = incoming_msg
        if class_choice in ['1', '2', '3', '4']:
            class_types = ['fe', 'se', 'te', 'be']
            session['class_type'] = class_types[int(class_choice) - 1]
            response.message("Great! Now please select a branch: \n1. AIML \n2. COMP \n3. CIVIL \n4. MECH \n5. CHEM \n6. EXTC \nType 'exit' to exit.")
            session['step'] = 'branch_selection'
        else:
            response.message("Invalid choice. Please select a valid class number or type 'exit' to exit.")
        return str(response)

    # Branch selection step
    if session.get('step') == 'branch_selection':
        branch_choice = incoming_msg
        branch_types = ['aiml', 'comp', 'civil', 'mech', 'chem', 'extc']
        if branch_choice in ['1', '2', '3', '4', '5', '6']:
            session['branch_type'] = branch_types[int(branch_choice) - 1]
            response.message("Please enter your roll number or type 'exit' to exit.")
            session['step'] = 'roll_number_input'
        else:
            response.message("Invalid choice. Please select a valid branch number or type 'exit' to exit.")
        return str(response)

    # Roll number input step
    if session.get('step') == 'roll_number_input':
        roll_number = incoming_msg
        session['roll_number'] = roll_number

        # Check if roll number is already verified
        if roll_number in session['verified_roll_numbers']:
            response.message("You have already verified your roll number. Please select an option: \n1. Average Attendance \n2. Subject Attendance \n3. Pending Fees \n4. Mess Bill \nType 'exit' to exit.")
            session['step'] = 'option_selection'
        else:
            primary_phone, secondary_phone = attendance_app.get_phone_numbers(roll_number, session['class_type'], session['branch_type'])
            if primary_phone is None:
                response.message("Roll number not found. Please check and try again or type 'exit' to exit.")
                return str(response)

            otp = attendance_app.generate_otp()
            attendance_app.store_otp(roll_number, otp, session['class_type'])

            if attendance_app.send_otp_via_whatsapp(primary_phone, secondary_phone, otp):
                response.message("OTP sent! Please enter the OTP to verify or type 'exit' to exit.")
                session['step'] = 'otp_verification'
            else:
                response.message("Failed to send OTP. Please try again later or type 'exit' to exit.")
                session.clear()  # Clear session on failure
        return str(response)

    # OTP verification step
    if session.get('step') == 'otp_verification':
        otp = incoming_msg
        if attendance_app.verify_otp(session['roll_number'], session['class_type'], otp):
            response.message("OTP verified! Please select an option: \n1. Average Attendance \n2. Subject Attendance \n3. Pending Fees \n4. Mess Bill \nType 'exit' to exit.")
            session['step'] = 'option_selection'
            # Add roll number to verified list
            session['verified_roll_numbers'].append(session['roll_number'])
        else:
            response.message("Invalid OTP. Please try again or type 'exit' to exit.")
        return str(response)

    # Option selection step
    if session.get('step') == 'option_selection':
        option_choice = incoming_msg
        if option_choice == '1':
            avg_attendance = attendance_app.get_average_attendance(session['roll_number'], session['class_type'], session['branch_type'])
            response.message(f"Your average attendance is: {avg_attendance}\nType 'exit' to exit.")
        elif option_choice == '2':
            response.message("Please select a subject:\n1. CN \n2. WC \n3. AI \n4. DWM \n5. SAIDS\nType 'exit' to exit.")
            session['step'] = 'subject_selection'
        elif option_choice == '3':
            pending_fees = attendance_app.get_pending_fees(session['roll_number'], session['class_type'], session['branch_type'])
            response.message(f"Your pending fees are: {pending_fees}\nType 'exit' to exit.")
        elif option_choice == '4':
            mess_bill = attendance_app.get_mess_bill(session['roll_number'], session['class_type'], session['branch_type'])
            response.message(f"Your mess bill is: {mess_bill}\nType 'exit' to exit.")
        else:
            response.message("Invalid option. Please select a valid number or type 'exit' to exit.")
        return str(response)

    # Subject selection step
    if session.get('step') == 'subject_selection':
        subject_choice = incoming_msg
        subjects = {'1': 'cn', '2': 'wc', '3': 'ai', '4': 'dwm', '5': 'saids'}

        subject = subjects.get(subject_choice)
        if subject:
            subject_attendance = attendance_app.get_subject_attendance(session['roll_number'], session['class_type'], session['branch_type'], subject)
            response.message(f"Your attendance for {subject.upper()} is: {subject_attendance}\nType 'exit' to exit.")
        else:
            response.message("Invalid subject selection. Please select a valid subject number or type 'exit' to exit.")
        return str(response)
