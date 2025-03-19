import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import os
from dotenv import load_dotenv
from typing import Dict, List, Optional

load_dotenv()

# Constants
APPOINTMENTS_FILE = "data/appointments.json"
SMTP_CONFIG = {
    "server": "smtp.gmail.com",
    "port": 587,
    "email": os.getenv("EMAIL_ADDRESS"),
    "password": os.getenv("EMAIL_PASSWORD"),
    "admin_email": "newturbony@gmail.com"
}

AVAILABLE_SLOTS = {
    "Monday": ["10:00", "11:00", "14:00", "15:00", "16:00"],
    "Tuesday": ["10:00", "11:00", "14:00", "15:00", "16:00"],
    "Wednesday": ["10:00", "11:00", "14:00", "15:00", "16:00"],
    "Thursday": ["10:00", "11:00", "14:00", "15:00", "16:00"],
    "Friday": ["10:00", "11:00", "14:00", "15:00", "16:00"],
    "Saturday": ["10:00", "11:00", "14:00"],
    "Sunday": ["10:00", "11:00", "14:00", "15:00"]
}

class EmailTemplate:
    @staticmethod
    def get_confirmation_template(appointment_data: Dict) -> Dict[str, Dict]:
        return {
            "user": {
                "subject": "Appointment Confirmation - New Turbo Education",
                "body": f"""
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
                """
            },
            "admin": {
                "subject": f"New Appointment: {appointment_data['name']}",
                "body": f"""
                <b>New appointment scheduled:</b>

                <b>Name:</b> {appointment_data['name']}
                <b>Email:</b> {appointment_data['email']}
                <b>Phone:</b> {appointment_data['phone']}
                <b>Date:</b> {appointment_data['date']}
                <b>Time:</b> {appointment_data['time']}
                """
            }
        }

    @staticmethod
    def get_cancellation_template(appointment_data: Dict) -> Dict[str, Dict]:
        return {
            "user": {
                "subject": "Appointment Cancellation Confirmation - New Turbo Education",
                "body": f"""
                <b>Dear {appointment_data['name']}</b>,

                Your appointment for {appointment_data['date']} at {appointment_data['time']} has been cancelled.

                If you would like to schedule a new appointment, please contact us or use our booking system.
                """
            },
            "admin": {
                "subject": f"Appointment Cancelled: {appointment_data['name']}",
                "body": f"""
                <b>Appointment cancelled:</b>

                <b>Name:</b> {appointment_data['name']}
                <b>Email:</b> {appointment_data['email']}
                <b>Phone:</b> {appointment_data['phone']}
                <b>Date:</b> {appointment_data['date']}
                <b>Time:</b> {appointment_data['time']}
                <b>Cancelled at:</b> {appointment_data.get('cancelled_at')}
                """
            }
        }

class EmailService:
    def __init__(self, config: Dict):
        self.config = config

    def send_email(self, to: str, subject: str, body: str) -> None:
        msg = MIMEMultipart()
        msg["From"] = self.config["email"]
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html"))

        with smtplib.SMTP(self.config["server"], self.config["port"]) as server:
            server.starttls()
            server.login(self.config["email"], self.config["password"])
            server.send_message(msg)

    def send_notifications(self, appointment_data: Dict, template_type: str) -> None:
        templates = (EmailTemplate.get_confirmation_template(appointment_data) 
                   if template_type == "confirmation" 
                   else EmailTemplate.get_cancellation_template(appointment_data))

        # Send to user
        self.send_email(
            appointment_data["email"],
            templates["user"]["subject"],
            templates["user"]["body"]
        )

        # Send to admin
        self.send_email(
            self.config["admin_email"],
            templates["admin"]["subject"],
            templates["admin"]["body"]
        )

class AppointmentManager:
    def __init__(self):
        self.email_service = EmailService(SMTP_CONFIG)

    def load_appointments(self) -> List[Dict]:
        if os.path.exists(APPOINTMENTS_FILE):
            with open(APPOINTMENTS_FILE, 'r') as f:
                return json.load(f)
        return []

    def save_appointments(self, appointments: List[Dict]) -> None:
        with open(APPOINTMENTS_FILE, 'w') as f:
            json.dump(appointments, f, indent=4)

    def validate_appointment(self, appointment_data: Dict) -> None:
        required_fields = ['name', 'email', 'phone', 'date', 'time']
        
        for field in required_fields:
            if field not in appointment_data:
                raise ValueError(f"Missing required field: {field}")
                
        if '@' not in appointment_data['email']:
            raise ValueError("Invalid email format")
            
        try:
            datetime.strptime(appointment_data['date'], '%Y-%m-%d')
        except ValueError:
            raise ValueError("Invalid date format")

    def save_appointment(self, appointment_data: Dict) -> None:
        self.validate_appointment(appointment_data)
        appointments = self.load_appointments()
        
        if any(appt['date'] == appointment_data['date'] and 
               appt['time'] == appointment_data['time'] and
               appt.get('status') != 'cancelled'
               for appt in appointments):
            raise ValueError("This time slot is already booked")
            
        appointments.append(appointment_data)
        self.save_appointments(appointments)
        self.email_service.send_notifications(appointment_data, "confirmation")

    def cancel_appointment(self, cancellation_data: Dict) -> Dict:
        appointments = self.load_appointments()
        
        for appointment in appointments:
            if (appointment['email'] == cancellation_data['email'] and
                appointment['date'] == cancellation_data['date'] and
                appointment['time'] == cancellation_data['time'] and
                appointment.get('status') != 'cancelled'):
                
                appointment['status'] = 'cancelled'
                appointment['cancelled_at'] = datetime.now().isoformat()
                
                self.save_appointments(appointments)
                self.email_service.send_notifications(appointment, "cancellation")
                return {"success": True}
        
        return {
            "success": False,
            "message": "No matching active appointment found"
        }

    def get_available_slots(self, date_str: str) -> List[str]:
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            day_of_week = date_obj.strftime('%A')
            
            if day_of_week not in AVAILABLE_SLOTS:
                return []
            
            booked_slots = [
                appt['time'] for appt in self.load_appointments()
                if appt['date'] == date_str and appt.get('status') != 'cancelled'
            ]
            
            return [
                slot for slot in AVAILABLE_SLOTS[day_of_week]
                if slot not in booked_slots
            ]
        except ValueError:
            return []

# Create a single instance to be used by the application
appointment_manager = AppointmentManager()

# Export the functions to maintain backwards compatibility
def save_appointment(appointment_data: Dict) -> None:
    appointment_manager.save_appointment(appointment_data)

def cancel_appointment(cancellation_data: Dict) -> Dict:
    return appointment_manager.cancel_appointment(cancellation_data)

def get_available_slots(date_str: str) -> List[str]:
    return appointment_manager.get_available_slots(date_str) 