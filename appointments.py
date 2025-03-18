import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

APPOINTMENTS_FILE = "data/appointments.json"
AVAILABLE_SLOTS = {
    "Monday": ["10:00", "11:00", "14:00", "15:00", "16:00"],
    "Tuesday": ["10:00", "11:00", "14:00", "15:00", "16:00"],
    "Wednesday": ["10:00", "11:00", "14:00", "15:00", "16:00"],
    "Thursday": ["10:00", "11:00", "14:00", "15:00", "16:00"],
    "Friday": ["10:00", "11:00", "14:00", "15:00", "16:00"],
    "Saturday": ["10:00", "11:00", "14:00"],
    "Sunday": ["10:00", "11:00", "14:00", "15:00"]
}

def load_appointments():
    if os.path.exists(APPOINTMENTS_FILE):
        with open(APPOINTMENTS_FILE, 'r') as f:
            return json.load(f)
    return []

def save_appointment(appointment_data):
    required_fields = ['name', 'email', 'phone', 'date', 'time']
    
    # Validate required fields
    for field in required_fields:
        if field not in appointment_data:
            raise ValueError(f"Missing required field: {field}")
            
    # Validate email format
    if '@' not in appointment_data['email']:
        raise ValueError("Invalid email format")
        
    # Validate date format
    try:
        datetime.strptime(appointment_data['date'], '%Y-%m-%d')
    except ValueError:
        raise ValueError("Invalid date format")
        
    appointments = load_appointments()
    
    # Check for duplicate appointments
    for appointment in appointments:
        if (appointment['date'] == appointment_data['date'] and 
            appointment['time'] == appointment_data['time']):
            raise ValueError("This time slot is already booked")
            
    appointments.append(appointment_data)
    with open(APPOINTMENTS_FILE, 'w') as f:
        json.dump(appointments, f, indent=4)

def get_available_slots(date_str):
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        day_of_week = date_obj.strftime('%A')
        
        if day_of_week not in AVAILABLE_SLOTS:
            return []
        
        # Get booked slots for this date
        booked_slots = [
            appt['time'] for appt in load_appointments()
            if appt['date'] == date_str
        ]
        
        # Return available slots
        return [
            slot for slot in AVAILABLE_SLOTS[day_of_week]
            if slot not in booked_slots
        ]
    except ValueError:
        return []

def send_confirmation_email(appointment_data):
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    sender_email = os.getenv("EMAIL_ADDRESS")
    sender_password = os.getenv("EMAIL_PASSWORD")

    # Create message for user
    user_msg = MIMEMultipart()
    user_msg["From"] = sender_email
    user_msg["To"] = f"{appointment_data['email']}, {sender_email}"
    user_msg["Subject"] = "Appointment Confirmation - New Turbo Education"
    
    user_body = f"""
    <b>Dear {appointment_data['name']}</b>,

    Your appointment has been confirmed for {appointment_data['date']} at {appointment_data['time']}.

    <b>Appointment Details:</b>
    <b>Name:</b> {appointment_data['name']}
    <b>Email:</b> {appointment_data['email']}
    <b>Phone:</b> {appointment_data['phone']}
    <b>Date:</b> {appointment_data['date']}
    <b>Time:</b> {appointment_data['time']}

    <b>Thank you for booking with us!</b>   
    If you need to reschedule or cancel, please contact us at +1 (718)-971-9914.
    We look forward to seeing you soon!
    
    <b>Best regards,</b>
    <b><i>New Turbo Education Team</i></b>
    <b><i>38-08 Union St, Flushing, NY 11354</i></b>
    """
    
    user_msg.attach(MIMEText(user_body, "html"))

    # Create message for admin
    admin_msg = MIMEMultipart()
    admin_msg["From"] = sender_email
    admin_msg["To"] = "newturbony@gmail.com"
    admin_msg["Subject"] = f"New Appointment: {appointment_data['name']}"
    
    admin_body = f"""
    <b>New appointment scheduled:</b>

    <b>Name:</b> {appointment_data['name']}
    <b>Email:</b> {appointment_data['email']}
    <b>Phone:</b> {appointment_data['phone']}
    <b>Date:</b> {appointment_data['date']}
    <b>Time:</b> {appointment_data['time']}
    """
    
    admin_msg.attach(MIMEText(admin_body, "plain"))

    # Send emails
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(user_msg)
        server.send_message(admin_msg) 