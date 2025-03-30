import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Union
from app.config.settings import DB_PATH, AVAILABLE_SLOTS
from app.services.email_service import EmailService
import requests

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AppointmentService:
    def __init__(self):
        self.email_service = EmailService()
        self.db_path = DB_PATH
        logger.info("Appointment service initialized")

    def get_db_connection(self) -> sqlite3.Connection:
        """Get a database connection"""
        try:
            return sqlite3.connect(self.db_path)
        except sqlite3.Error as e:
            logger.error(f"Database connection error: {str(e)}")
            raise

    def check_duplicate_appointment(self, appointment_time: str) -> bool:
        """Check if an appointment already exists for the given time"""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM appointments 
                    WHERE datetime(appointment_time) = datetime(?)
                    AND status = 'scheduled'
                """, (appointment_time,))
                return cursor.fetchone()[0] > 0
        except sqlite3.Error as e:
            logger.error(f"Error checking duplicate appointment: {str(e)}")
            raise ValueError(f"Database error: {str(e)}")

    def save_appointment(self, appointment_data: Dict) -> None:
        """
        Save a new appointment and send email notifications
        
        Args:
            appointment_data: Dictionary containing appointment details
            
        Raises:
            ValueError: If appointment data is invalid or if there's a database error
        """
        logger.info(f"Processing appointment for: {appointment_data.get('email')}")
        
        # Validate appointment data
        try:
            self.validate_appointment(appointment_data)
        except ValueError as e:
            logger.warning(f"Appointment validation failed: {str(e)}")
            raise
        
        # Normalize email for case-insensitive search
        appointment_data['email'] = appointment_data['email'].lower().strip()
        
        # Check for duplicate appointment
        appointment_time = f"{appointment_data['date']} {appointment_data['time']}"
        logger.debug(f"Checking for duplicate appointment at: {appointment_time}")
        
        if self.check_duplicate_appointment(appointment_time):
            logger.warning(f"Duplicate appointment attempt for {appointment_time}")
            raise ValueError("This time slot is already booked")
        
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                
                # First, check if user exists
                logger.debug(f"Checking if user exists with email: {appointment_data['email']}")
                cursor.execute("""
                    SELECT id FROM users 
                    WHERE LOWER(email) = ? OR phone = ?
                """, (appointment_data['email'], appointment_data['phone']))
                
                user = cursor.fetchone()
                if not user:
                    logger.info(f"Creating new user: {appointment_data['email']}")
                    # Create new user
                    cursor.execute("""
                        INSERT INTO users (name, email, phone)
                        VALUES (?, ?, ?)
                    """, (appointment_data['name'], appointment_data['email'], appointment_data['phone']))
                    user_id = cursor.lastrowid
                    logger.info(f"Created new user with ID: {user_id}")
                else:
                    user_id = user[0]
                    logger.info(f"Found existing user with ID: {user_id}")
                
                # Create appointment
                logger.info(f"Creating appointment for user {user_id} at {appointment_time}")
                cursor.execute("""
                    INSERT INTO appointments (user_id, appointment_time, status)
                    VALUES (?, ?, 'scheduled')
                """, (user_id, appointment_time))
                
                conn.commit()
                logger.info(f"Appointment saved successfully for {appointment_data['email']}")
                
                # Send email notifications
                logger.info("Sending email notifications")
                email_success, email_error = self.email_service.send_appointment_notifications(
                    appointment_data, "confirmation"
                )
                
                if not email_success:
                    logger.warning(f"Email notification failed: {email_error}")
                    # We don't raise an exception here since the appointment is saved
                    # but we log the issue for follow-up
                
        except sqlite3.Error as e:
            logger.error(f"Database error in save_appointment: {str(e)}")
            raise ValueError(f"Database error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in save_appointment: {str(e)}")
            raise

    def cancel_appointment(self, cancellation_data: Dict) -> Dict:
        """
        Cancel an existing appointment
        
        Args:
            cancellation_data: Dictionary containing email, date, and time
            
        Returns:
            Dictionary with success status and message
        """
        logger.info(f"Processing cancellation for: {cancellation_data.get('email')}")
        
        try:
            # Normalize email for case-insensitive search
            user_email = cancellation_data.get('email', '').lower().strip()
            
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Get appointment and user details
                cursor.execute("""
                    SELECT u.name, u.email, u.phone, a.appointment_time, a.id
                    FROM appointments a
                    JOIN users u ON a.user_id = u.id
                    WHERE LOWER(u.email) = ? 
                    AND date(a.appointment_time) = ?
                    AND strftime('%H:%M', a.appointment_time) = ?
                    AND a.status = ?
                """, (user_email, cancellation_data['date'], cancellation_data['time'], AppointmentStatus.SCHEDULED))
                
                result = cursor.fetchone()
                if not result:
                    logger.warning(f"No matching appointment found for cancellation: {cancellation_data}")
                    return {
                        "success": False,
                        "message": "No matching active appointment found"
                    }
                
                # Update appointment status
                cursor.execute("""
                    UPDATE appointments 
                    SET status = ?
                    WHERE id = ?
                """, (AppointmentStatus.CANCELLED, result[4]))
                
                conn.commit()
                logger.info(f"Appointment cancelled successfully: ID {result[4]}")
                
                # Prepare data for email notification
                try:
                    # 确保时间格式正确
                    appointment_time = datetime.strptime(result[3], '%Y-%m-%d %H:%M:%S')
                    email_data = {
                        'name': result[0],
                        'email': result[1],
                        'phone': result[2],
                        'date': appointment_time.strftime('%Y-%m-%d'),
                        'time': appointment_time.strftime('%H:%M')
                    }
                except ValueError as e:
                    logger.error(f"Error formatting appointment time: {str(e)}")
                    # 即使时间格式化失败，我们仍然使用原始数据
                    email_data = {
                        'name': result[0],
                        'email': result[1],
                        'phone': result[2],
                        'date': cancellation_data['date'],
                        'time': cancellation_data['time']
                    }
                
                # Send email notifications
                email_success, email_error = self.email_service.send_appointment_notifications(
                    email_data, "cancellation"
                )
                
                if not email_success:
                    logger.warning(f"Cancellation email notification failed: {email_error}")
                
                return {"success": True}
                
        except sqlite3.Error as e:
            logger.error(f"Database error in cancel_appointment: {str(e)}")
            return {
                "success": False,
                "message": f"Database error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Unexpected error in cancel_appointment: {str(e)}")
            return {
                "success": False,
                "message": f"An unexpected error occurred: {str(e)}"
            }

    def get_available_slots(self, date_str: str) -> List[str]:
        """
        Get available time slots for a given date
        
        Args:
            date_str: Date string in YYYY-MM-DD format
            
        Returns:
            List of available time slots
        """
        logger.info(f"Getting available slots for date: {date_str}")
        
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            day_of_week = date_obj.strftime('%A')
            
            if day_of_week not in AVAILABLE_SLOTS:
                logger.warning(f"No slots available for day of week: {day_of_week}")
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
            
            available_slots = [
                slot for slot in AVAILABLE_SLOTS[day_of_week]
                if slot not in booked_slots
            ]
            
            logger.info(f"Found {len(available_slots)} available slots for {date_str}")
            return available_slots
            
        except ValueError as e:
            logger.error(f"Invalid date format: {date_str} - {str(e)}")
            return []
        except sqlite3.Error as e:
            logger.error(f"Database error in get_available_slots: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in get_available_slots: {str(e)}")
            return []

    def validate_appointment(self, appointment_data: Dict) -> None:
        """
        Validate appointment data
        
        Args:
            appointment_data: Dictionary containing appointment details
            
        Raises:
            ValueError: If data is invalid
        """
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

    def get_appointment_history(self, email: str) -> List[tuple]:
        """
        Get appointment history for a user
        
        Args:
            email: User's email address
            
        Returns:
            List of tuples containing appointment details
        """
        logger.info(f"Fetching appointment history for: {email}")
        
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Get all appointments for the user
                cursor.execute("""
                    SELECT 
                        datetime(a.appointment_time) as appointment_time,
                        u.name,
                        u.email,
                        u.phone,
                        a.status
                    FROM appointments a
                    JOIN users u ON a.user_id = u.id
                    WHERE LOWER(u.email) = ?
                    ORDER BY a.appointment_time DESC
                """, (email.lower().strip(),))
                
                appointments = cursor.fetchall()
                logger.info(f"Found {len(appointments)} appointments for {email}")
                
                # Format the appointment times
                formatted_appointments = []
                for appt in appointments:
                    try:
                        # Parse the datetime and ensure it has seconds
                        appt_time = datetime.strptime(appt[0], '%Y-%m-%d %H:%M')
                        formatted_time = appt_time.strftime('%Y-%m-%d %H:%M:%S')
                        formatted_appointments.append(
                            (formatted_time,) + appt[1:]
                        )
                    except ValueError:
                        # If the time already has seconds or any other format, use it as is
                        formatted_appointments.append(appt)
                
                return formatted_appointments
                
        except sqlite3.Error as e:
            logger.error(f"Database error in get_appointment_history: {str(e)}")
            raise ValueError(f"Database error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in get_appointment_history: {str(e)}")
            raise

    def get_active_appointments(self, name: str) -> List[Dict]:
        """
        获取用户的所有有效预约
        Args:
            name (str): 用户姓名
        Returns:
            List[Dict]: 预约列表
        """
        if not name:
            logger.warning("Name is required for getting active appointments")
            return []
            
        try:
            logger.info(f"Getting active appointments for name: {name}")
            
            query = """
                SELECT 
                    a.id,
                    u.name,
                    u.email,
                    u.phone,
                    date(a.appointment_time) as appointment_date,
                    strftime('%H:%M', a.appointment_time) as appointment_time,
                    a.status,
                    a.created_at
                FROM appointments a
                JOIN users u ON a.user_id = u.id
                WHERE LOWER(u.name) = LOWER(?)
                AND a.status = 'scheduled'
                ORDER BY a.appointment_time DESC
            """
            
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (name.lower(),))
                appointments = cursor.fetchall()
                
                if not appointments:
                    logger.info(f"No active appointments found for name: {name}")
                    return []
                    
                # 转换结果为字典列表
                result = []
                for appointment in appointments:
                    appointment_dict = {
                        'id': appointment[0],
                        'name': appointment[1],
                        'email': appointment[2],
                        'phone': appointment[3],
                        'date': appointment[4],
                        'time': appointment[5],
                        'status': appointment[6],
                        'created_at': appointment[7]
                    }
                    result.append(appointment_dict)
                    
                logger.info(f"Found {len(result)} active appointments for name: {name}")
                return result
                
        except sqlite3.Error as e:
            logger.error(f"Database error in get_active_appointments: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in get_active_appointments: {str(e)}")
            raise

    def fetch_appointments(self, email: str = None, name: str = None, query: str = None, params: list = None) -> Dict[str, Union[bool, str, List]]:
        """Fetches appointments from the API with improved error handling"""
        try:
            logger.info(f"Fetching appointments for: {email} with name: {name}")
            
            # 构建请求数据
            request_data = {}
            if email:
                request_data["email"] = email
            if name:
                request_data["name"] = name
            
            response = requests.post(
                f"{API_URL}/check_appointments",
                json=request_data,
                timeout=10
            )
            
            logger.info(f"API response status: {response.status_code}")
            result = self._handle_api_response(response)
            
            # Add status code to result for better error handling
            result['status_code'] = response.status_code
            return result
                
        except requests.exceptions.Timeout:
            logger.error("Request timed out when fetching appointments")
            return {
                'success': False,
                'message': "Request timed out. The server is taking too long to respond."
            }
        except requests.exceptions.ConnectionError:
            logger.error("Connection error when fetching appointments")
            return {
                'success': False,
                'message': "Could not connect to the server. Please try again later."
            }
        except Exception as e:
            logger.error(f"Unexpected error fetching appointments: {str(e)}")
            return {
                'success': False,
                'message': f"An error occurred: {str(e)}"
            }

    def _handle_api_response(self, response):
        # This method should be implemented to handle the API response
        # It should return a dictionary with 'success', 'message', and 'data' keys
        # For now, we'll just return the response text as the message
        return {
            'success': True,
            'message': response.text
        } 