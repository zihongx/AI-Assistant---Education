import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import os
from dotenv import load_dotenv
from typing import Dict, List, Optional
import sqlite3

load_dotenv()

# Constants
DB_PATH = os.path.join(os.getcwd(), "data", "appointments.db")
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
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333;">
                    <div style="text-align: center; padding: 20px 0;">
                        <h1 style="color: #1f77b4; margin: 0;">Appointment Confirmation</h1>
                        <p style="color: #666; font-size: 16px;">New Turbo Education</p>
                    </div>
                    
                    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                        <p style="font-size: 16px; margin-bottom: 20px;">Dear <strong>{appointment_data['name']}</strong>,</p>
                        
                        <p style="font-size: 16px; margin-bottom: 20px;">Your appointment has been successfully scheduled!</p>
                        
                        <div style="background-color: white; padding: 15px; border-radius: 6px; border-left: 4px solid #1f77b4;">
                            <h2 style="color: #1f77b4; font-size: 18px; margin: 0 0 15px 0;">📅 Appointment Details</h2>
                            <p style="margin: 5px 0;"><strong>Date:</strong> {appointment_data['date']}</p>
                            <p style="margin: 5px 0;"><strong>Time:</strong> {appointment_data['time']}</p>
                            <p style="margin: 5px 0;"><strong>Name:</strong> {appointment_data['name']}</p>
                            <p style="margin: 5px 0;"><strong>Email:</strong> {appointment_data['email']}</p>
                            <p style="margin: 5px 0;"><strong>Phone:</strong> {appointment_data['phone']}</p>
                        </div>
                        
                        <div style="margin-top: 30px;">
                            <h3 style="color: #1f77b4; font-size: 16px;">Important Information:</h3>
                            <ul style="list-style-type: none; padding: 0;">
                                <li style="margin: 10px 0;">⏰ Please arrive 5-10 minutes before your scheduled time.</li>
                                <li style="margin: 10px 0;">📍 Location: 133-36 41st Road, Suite 2F, Flushing, NY 11355</li>
                                <li style="margin: 10px 0;">📱 Need to reschedule? Call us at +1 (718)-971-9914</li>
                            </ul>
                        </div>
                    </div>
                    
                    <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee;">
                        <p style="color: #666;">We look forward to seeing you!</p>
                        <p style="color: #666; font-size: 12px;">© 2024 New Turbo Education. All rights reserved.</p>
                    </div>
                </div>
                """
            },
            "admin": {
                "subject": f"New Appointment: {appointment_data['name']}",
                "body": f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333;">
                    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px;">
                        <h2 style="color: #1f77b4; margin: 0 0 20px 0;">🎉 New Appointment Scheduled</h2>
                        
                        <div style="background-color: white; padding: 15px; border-radius: 6px; border-left: 4px solid #1f77b4;">
                            <h3 style="color: #1f77b4; font-size: 16px; margin: 0 0 15px 0;">📋 Appointment Details</h3>
                            <p style="margin: 5px 0;"><strong>Date:</strong> {appointment_data['date']}</p>
                            <p style="margin: 5px 0;"><strong>Time:</strong> {appointment_data['time']}</p>
                            <p style="margin: 5px 0;"><strong>Name:</strong> {appointment_data['name']}</p>
                            <p style="margin: 5px 0;"><strong>Email:</strong> {appointment_data['email']}</p>
                            <p style="margin: 5px 0;"><strong>Phone:</strong> {appointment_data['phone']}</p>
                        </div>
                    </div>
                </div>
                """
            }
        }

    @staticmethod
    def get_cancellation_template(appointment_data: Dict) -> Dict[str, Dict]:
        return {
            "user": {
                "subject": "Appointment Cancellation Confirmation - New Turbo Education",
                "body": f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333;">
                    <div style="text-align: center; padding: 20px 0;">
                        <h1 style="color: #dc3545; margin: 0;">Appointment Cancellation</h1>
                        <p style="color: #666; font-size: 16px;">New Turbo Education</p>
                    </div>
                    
                    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                        <p style="font-size: 16px; margin-bottom: 20px;">Dear <strong>{appointment_data['name']}</strong>,</p>
                        
                        <p style="font-size: 16px; margin-bottom: 20px;">Your appointment has been successfully cancelled.</p>
                        
                        <div style="background-color: white; padding: 15px; border-radius: 6px; border-left: 4px solid #dc3545;">
                            <h2 style="color: #dc3545; font-size: 18px; margin: 0 0 15px 0;">📅 Cancelled Appointment Details</h2>
                            <p style="margin: 5px 0;"><strong>Date:</strong> {appointment_data['date']}</p>
                            <p style="margin: 5px 0;"><strong>Time:</strong> {appointment_data['time']}</p>
                        </div>
                        
                        <div style="margin-top: 30px;">
                            <p style="font-size: 16px;">Would you like to schedule a new appointment?</p>
                            <ul style="list-style-type: none; padding: 0;">
                                <li style="margin: 10px 0;">📱 Call us: +1 (718)-971-9914</li>
                                <li style="margin: 10px 0;">✉️ Email: newturbony@gmail.com</li>
                                <li style="margin: 10px 0;">🌐 Visit our website to book online</li>
                            </ul>
                        </div>
                    </div>
                    
                    <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee;">
                        <p style="color: #666;">Thank you for your understanding.</p>
                        <p style="color: #666; font-size: 12px;">© 2024 New Turbo Education. All rights reserved.</p>
                    </div>
                </div>
                """
            },
            "admin": {
                "subject": f"Appointment Cancelled: {appointment_data['name']}",
                "body": f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333;">
                    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px;">
                        <h2 style="color: #dc3545; margin: 0 0 20px 0;">❌ Appointment Cancelled</h2>
                        
                        <div style="background-color: white; padding: 15px; border-radius: 6px; border-left: 4px solid #dc3545;">
                            <h3 style="color: #dc3545; font-size: 16px; margin: 0 0 15px 0;">📋 Cancelled Appointment Details</h3>
                            <p style="margin: 5px 0;"><strong>Date:</strong> {appointment_data['date']}</p>
                            <p style="margin: 5px 0;"><strong>Time:</strong> {appointment_data['time']}</p>
                            <p style="margin: 5px 0;"><strong>Name:</strong> {appointment_data['name']}</p>
                            <p style="margin: 5px 0;"><strong>Email:</strong> {appointment_data['email']}</p>
                            <p style="margin: 5px 0;"><strong>Phone:</strong> {appointment_data['phone']}</p>
                            <p style="margin: 5px 0;"><strong>Cancelled at:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                        </div>
                    </div>
                </div>
                """
            }
        }

class EmailService:
    def __init__(self, config: Dict):
        self.config = config
        print(f"Email service initialized with config: {config}")  # Debug log

    def send_email(self, to: str, subject: str, body: str) -> None:
        print(f"Attempting to send email to: {to}")  # Debug log
        print(f"Subject: {subject}")  # Debug log
        msg = MIMEMultipart()
        msg["From"] = self.config["email"]
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html"))

        try:
            with smtplib.SMTP(self.config["server"], self.config["port"]) as server:
                print("Connected to SMTP server")  # Debug log
                server.starttls()
                print("Started TLS")  # Debug log
                server.login(self.config["email"], self.config["password"])
                print("Logged in successfully")  # Debug log
                server.send_message(msg)
                print("Email sent successfully")  # Debug log
        except Exception as e:
            print(f"Error sending email: {str(e)}")  # Debug log
            raise

    def send_notifications(self, appointment_data: Dict, template_type: str) -> None:
        print(f"Sending {template_type} notifications for appointment: {appointment_data}")  # Debug log
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
        self.db_path = DB_PATH

    def get_db_connection(self):
        return sqlite3.connect(self.db_path)

    def check_duplicate_appointment(self, appointment_time: str) -> bool:
        """Check if an appointment already exists for the given time"""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM appointments 
                WHERE datetime(appointment_time) = datetime(?)
                AND status = 'scheduled'
            """, (appointment_time,))
            return cursor.fetchone()[0] > 0

    def save_appointment(self, appointment_data: Dict) -> None:
        print(f"Validating appointment data: {appointment_data}")  # Debug log
        self.validate_appointment(appointment_data)
        
        # Check for duplicate appointment
        appointment_time = f"{appointment_data['date']} {appointment_data['time']}"
        print(f"Checking for duplicate appointment at: {appointment_time}")  # Debug log
        if self.check_duplicate_appointment(appointment_time):
            raise ValueError("This time slot is already booked")
        
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                
                # First, check if user exists
                print(f"Checking if user exists with email: {appointment_data['email']}")  # Debug log
                cursor.execute("""
                    SELECT id FROM users 
                    WHERE email = ? OR phone = ?
                """, (appointment_data['email'], appointment_data['phone']))
                
                user = cursor.fetchone()
                if not user:
                    print("Creating new user")  # Debug log
                    # Create new user
                    cursor.execute("""
                        INSERT INTO users (name, email, phone)
                        VALUES (?, ?, ?)
                    """, (appointment_data['name'], appointment_data['email'], appointment_data['phone']))
                    user_id = cursor.lastrowid
                    print(f"Created new user with ID: {user_id}")  # Debug log
                else:
                    user_id = user[0]
                    print(f"Found existing user with ID: {user_id}")  # Debug log
                
                # Create appointment
                print(f"Creating appointment for user {user_id} at {appointment_time}")  # Debug log
                cursor.execute("""
                    INSERT INTO appointments (user_id, appointment_time, status)
                    VALUES (?, ?, 'scheduled')
                """, (user_id, appointment_time))
                
                conn.commit()
                print("Committed changes to database")  # Debug log
                
                # Get full appointment data for email
                print("Sending email notifications")  # Debug log
                self.email_service.send_notifications(appointment_data, "confirmation")
                print("Email notifications sent")  # Debug log
        except sqlite3.Error as e:
            print(f"Database error: {str(e)}")  # Debug log
            raise ValueError(f"Database error: {str(e)}")
        except Exception as e:
            print(f"Error in save_appointment: {str(e)}")  # Debug log
            raise

    def cancel_appointment(self, cancellation_data: Dict) -> Dict:
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get appointment and user details
            cursor.execute("""
                SELECT u.name, u.email, u.phone, a.appointment_time, a.id
                FROM appointments a
                JOIN users u ON a.user_id = u.id
                WHERE u.email = ? 
                AND datetime(a.appointment_time) = datetime(?)
                AND a.status = 'scheduled'
            """, (cancellation_data['email'], f"{cancellation_data['date']} {cancellation_data['time']}"))
            
            result = cursor.fetchone()
            if not result:
                return {
                    "success": False,
                    "message": "No matching active appointment found"
                }
            
            # Update appointment status
            cursor.execute("""
                UPDATE appointments 
                SET status = 'canceled'
                WHERE id = ?
            """, (result[4],))
            
            conn.commit()
            
            # Prepare data for email notification
            appointment_data = {
                'name': result[0],
                'email': result[1],
                'phone': result[2],
                'date': cancellation_data['date'],
                'time': cancellation_data['time']
            }
            
            self.email_service.send_notifications(appointment_data, "cancellation")
            return {"success": True}

    def get_available_slots(self, date_str: str) -> List[str]:
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            day_of_week = date_obj.strftime('%A')
            
            if day_of_week not in AVAILABLE_SLOTS:
                return []
            
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT strftime('%H:%M', appointment_time)
                    FROM appointments
                    WHERE date(appointment_time) = ?
                    AND status = 'scheduled'
                """, (date_str,))
                
                booked_slots = [row[0] for row in cursor.fetchall()]
            
            return [
                slot for slot in AVAILABLE_SLOTS[day_of_week]
                if slot not in booked_slots
            ]
        except ValueError:
            return []

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

    def get_appointment_history(self, email: str) -> List[Dict]:
        """Get all appointments (including cancelled ones) for a user"""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    u.name,
                    u.email,
                    u.phone,
                    date(a.appointment_time) as date,
                    strftime('%H:%M', a.appointment_time) as time,
                    a.status,
                    a.appointment_time
                FROM appointments a
                JOIN users u ON a.user_id = u.id
                WHERE u.email = ?
                ORDER BY a.appointment_time DESC
            """, (email,))
            
            appointments = []
            for row in cursor.fetchall():
                appointments.append({
                    'name': row[0],
                    'email': row[1],
                    'phone': row[2],
                    'date': row[3],
                    'time': row[4],
                    'status': row[5],
                    'appointment_time': row[6]
                })
            return appointments

# Create a single instance to be used by the application
appointment_manager = AppointmentManager()

# Export the functions to maintain backwards compatibility
def save_appointment(appointment_data: Dict) -> None:
    appointment_manager.save_appointment(appointment_data)

def cancel_appointment(cancellation_data: Dict) -> Dict:
    return appointment_manager.cancel_appointment(cancellation_data)

def get_available_slots(date_str: str) -> List[str]:
    return appointment_manager.get_available_slots(date_str)