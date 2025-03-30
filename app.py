import os
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv, find_dotenv
from datetime import datetime
from app.services.chat import ChatService
from app.services.intent_detection import IntentDetectionService
from app.services.vector_store import VectorStoreService
from app.services.appointment_service import AppointmentService
from app.utils.database.db_utils import init_db
from app.config.settings import DB_PATH, MODEL_CONFIG, SYSTEM_PROMPT, SMTP_CONFIG
import sqlite3
import requests

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

_ = load_dotenv(find_dotenv())
openai_api_key = os.getenv("OPENAI_API_KEY")

if not openai_api_key:
    raise ValueError("OpenAI API key is missing. Please set it in .env")

# Initialize OpenAI client
client = OpenAI()

app = Flask(__name__)
CORS(app)

# Initialize services
logger.info("Initializing services...")
chat_service = ChatService()
intent_detector = IntentDetectionService()
vector_store = VectorStoreService()
appointment_service = AppointmentService()
logger.info("Services initialized successfully")

@app.route('/detect_intent', methods=['POST'])
def detect_intent_route():
    try:
        data = request.json
        if not data or 'query' not in data:
            return jsonify({"error": "No query provided"}), 400
        
        user_query = data.get("query")
        intent_data = intent_detector.detect_intent(user_query)
        return jsonify({"intent_data": intent_data})
        
    except Exception as e:
        logger.error(f"Error in detect_intent: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/query', methods=['POST'])
def answer_query():
    try:
        data = request.json
        if not data or 'query' not in data:
            logger.warning("No query provided")
            return jsonify({"error": "No query provided"}), 400
        
        user_query = data.get("query").lower().strip()
        conversation_history = data.get("conversation_history", [])
        
        # Use hybrid intent detection approach
        intent_data = chat_service.get_hybrid_intent(user_query, conversation_history)
        logger.info(f"Hybrid intent detected: {intent_data.get('intent')} with confidence {intent_data.get('confidence', 0)}")
        
        # If it's an appointment intent, return special response
        if intent_data.get("intent") == "schedule_appointment" and intent_data.get("confidence", 0) > chat_service.confidence_threshold_medium:
            bilingual_response = """I'd be happy to help you schedule an appointment with New Turbo Education! Our tutors specialize in SAT, AP, ACT, SHSAT, TOEFL preparation and more. Making an appointment is quick and easy.

我很乐意帮您预约新突破教育的课程！我们的老师专注于SAT、AP、ACT、SHSAT、托福等考试的备考辅导。预约过程简单快捷。

Please select your preferred date and time in the form below:
请在下方表格中选择您偏好的日期和时间："""
            
            return jsonify({
                "answer": bilingual_response,
                "intent": "schedule_appointment"
            })
        
        # Otherwise proceed with regular query
        answer = chat_service.get_completion(user_query, conversation_history)
        return jsonify({
            "answer": answer, 
            "intent": intent_data.get("intent", "general_query")
        })
    except Exception as e:
        logger.error(f"Error in answer_query: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/schedule', methods=['POST'])
def handle_scheduling():
    try:
        data = request.json
        logger.info(f"Received scheduling request for action: {data.get('action')}")
        action = data.get('action')
        
        if action == 'check_availability':
            date = data.get('date')
            logger.info(f"Checking availability for date: {date}")
            available_slots = appointment_service.get_available_slots(date)
            logger.info(f"Found {len(available_slots)} available slots")
            return jsonify({
                "available_slots": available_slots
            })
            
        elif action == 'book_appointment':
            appointment_data = {
                'name': data.get('name'),
                'email': data.get('email'),
                'phone': data.get('phone'),
                'date': data.get('date'),
                'time': data.get('time')
            }
            logger.info(f"Attempting to save appointment for: {appointment_data.get('email')}")
            
            try:
                # Validate the data before saving
                if not all([appointment_data['name'], appointment_data['email'], 
                          appointment_data['phone'], appointment_data['date'], 
                          appointment_data['time']]):
                    logger.warning("Missing required fields in appointment data")
                    raise ValueError("Missing required fields")
                
                # Check if the date is valid
                try:
                    datetime.strptime(appointment_data['date'], '%Y-%m-%d')
                except ValueError:
                    logger.warning(f"Invalid date format: {appointment_data['date']}")
                    raise ValueError("Invalid date format")
                
                # Check if the time is valid
                try:
                    datetime.strptime(appointment_data['time'], '%H:%M')
                except ValueError:
                    logger.warning(f"Invalid time format: {appointment_data['time']}")
                    raise ValueError("Invalid time format")
                
                # Initialize database if it doesn't exist
                init_db()
                
                appointment_service.save_appointment(appointment_data)
                logger.info(f"Appointment saved successfully for {appointment_data['email']}")
                return jsonify({
                    "success": True,
                    "message": "Appointment scheduled successfully"
                })
            except Exception as e:
                logger.error(f"Error saving appointment: {str(e)}")
                return jsonify({
                    "success": False,
                    "message": str(e)
                }), 400
            
    except Exception as e:
        logger.error(f"Unexpected error in handle_scheduling: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/cancel_appointment', methods=['POST'])
def handle_cancellation():
    try:
        data = request.json
        if not data or 'email' not in data or 'date' not in data or 'time' not in data:
            logger.warning("Missing required fields for cancellation")
            return jsonify({"error": "Missing required fields (email, date, time)"}), 400
        
        # 只使用 email 进行查询
        user_email = data.get('email', '').lower().strip()
        logger.info(f"Attempting to cancel appointment for email: {user_email}")
        
        try:
            with appointment_service.get_db_connection() as conn:
                cursor = conn.cursor()
                
                # 只通过 email 查找用户
                cursor.execute("""
                    SELECT id, name, email, phone
                    FROM users 
                    WHERE LOWER(email) = ?
                """, (user_email,))
                user = cursor.fetchone()
                
                if not user:
                    logger.warning(f"No user found with email: {user_email}")
                    return jsonify({
                        "success": False,
                        "message": "No user found with this email"
                    }), 404
                
                # 查找并取消特定预约
                cursor.execute("""
                    UPDATE appointments 
                    SET status = 'canceled'
                    WHERE user_id = ?
                    AND date(appointment_time) = ?
                    AND strftime('%H:%M', appointment_time) = ?
                    AND status = 'scheduled'
                    RETURNING id, appointment_time
                """, (user[0], data['date'], data['time']))
                
                cancelled = cursor.fetchone()
                conn.commit()
                
                if cancelled:
                    logger.info("Appointment cancelled successfully")
                    
                    # 准备邮件数据
                    try:
                        # 确保时间格式正确
                        appointment_time = datetime.strptime(cancelled[1], '%Y-%m-%d %H:%M:%S')
                        email_data = {
                            'name': user[1],
                            'email': user[2],
                            'phone': user[3],
                            'date': appointment_time.strftime('%Y-%m-%d'),
                            'time': appointment_time.strftime('%H:%M')
                        }
                        
                        # 发送邮件通知
                        try:
                            # 发送给用户的取消确认邮件
                            user_email_data = {
                                'to_email': user[2],
                                'subject': 'Appointment Cancellation Confirmation | 预约取消确认',
                                'template': 'cancellation_confirmation',
                                'data': email_data
                            }
                            
                            # 发送给管理员的取消通知邮件
                            admin_email_data = {
                                'to_email': SMTP_CONFIG['admin_email'],
                                'subject': 'Appointment Cancellation Notification | 预约取消通知',
                                'template': 'cancellation_notification',
                                'data': email_data
                            }
                            
                            # 发送邮件
                            response = requests.post(
                                f"{API_URL}/send_email",
                                json=user_email_data,
                                timeout=10
                            )
                            
                            if response.status_code != 200:
                                logger.warning(f"Failed to send user cancellation email: {response.text}")
                            
                            response = requests.post(
                                f"{API_URL}/send_email",
                                json=admin_email_data,
                                timeout=10
                            )
                            
                            if response.status_code != 200:
                                logger.warning(f"Failed to send admin cancellation email: {response.text}")
                                
                        except Exception as e:
                            logger.error(f"Error sending cancellation emails: {str(e)}")
                            # 不中断流程，继续返回成功状态
                            
                    except ValueError as e:
                        logger.error(f"Error formatting appointment time: {str(e)}")
                        # 即使时间格式化失败，我们仍然认为取消是成功的
                        email_data = {
                            'name': user[1],
                            'email': user[2],
                            'phone': user[3],
                            'date': data['date'],
                            'time': data['time']
                        }
                    
                    return jsonify({
                        "success": True,
                        "message": "Appointment cancelled successfully"
                    })
                else:
                    logger.warning("No matching active appointment found")
                    return jsonify({
                        "success": False,
                        "message": "No matching active appointment found"
                    }), 404
                    
        except sqlite3.Error as e:
            logger.error(f"Database error in handle_cancellation: {str(e)}")
            return jsonify({
                "success": False,
                "message": f"Database error: {str(e)}"
            }), 500
            
    except Exception as e:
        logger.error(f"Error in handle_cancellation: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/send_email', methods=['POST'])
def send_email():
    try:
        data = request.json
        if not data or 'to_email' not in data or 'subject' not in data or 'template' not in data:
            return jsonify({"error": "Missing required fields"}), 400
            
        to_email = data['to_email']
        subject = data['subject']
        template = data['template']
        template_data = data.get('data', {})
        
        # 根据模板类型选择邮件内容
        if template == 'cancellation_confirmation':
            # 用户取消确认邮件模板
            html_content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333;">
                <div style="text-align: center; padding: 20px 0;">
                    <h1 style="color: #dc3545; margin: 0;">Appointment Cancellation</h1>
                    <p style="color: #666; font-size: 16px;">New Turbo Education</p>
                </div>
                
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <p style="font-size: 16px; margin-bottom: 20px;">Dear <strong>{template_data.get('name', 'Student')}</strong>,</p>
                    
                    <p style="font-size: 16px; margin-bottom: 20px;">Your appointment has been successfully cancelled.</p>
                    
                    <div style="background-color: white; padding: 15px; border-radius: 6px; border-left: 4px solid #dc3545;">
                        <h2 style="color: #dc3545; font-size: 18px; margin: 0 0 15px 0;">📅 Cancelled Appointment Details</h2>
                        <p style="margin: 5px 0;"><strong>Date:</strong> {template_data.get('date', 'N/A')}</p>
                        <p style="margin: 5px 0;"><strong>Time:</strong> {template_data.get('time', 'N/A')}</p>
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
        elif template == 'cancellation_notification':
            # 管理员取消通知邮件模板
            html_content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333;">
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px;">
                    <h2 style="color: #dc3545; margin: 0 0 20px 0;">❌ Appointment Cancelled</h2>
                    
                    <div style="background-color: white; padding: 15px; border-radius: 6px; border-left: 4px solid #dc3545;">
                        <h3 style="color: #dc3545; font-size: 16px; margin: 0 0 15px 0;">📋 Cancelled Appointment Details</h3>
                        <p style="margin: 5px 0;"><strong>Name:</strong> {template_data.get('name', 'N/A')}</p>
                        <p style="margin: 5px 0;"><strong>Email:</strong> {template_data.get('email', 'N/A')}</p>
                        <p style="margin: 5px 0;"><strong>Phone:</strong> {template_data.get('phone', 'N/A')}</p>
                        <p style="margin: 5px 0;"><strong>Date:</strong> {template_data.get('date', 'N/A')}</p>
                        <p style="margin: 5px 0;"><strong>Time:</strong> {template_data.get('time', 'N/A')}</p>
                        <p style="margin: 5px 0;"><strong>Cancelled at:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    </div>
                </div>
            </div>
            """
        else:
            return jsonify({"error": "Invalid template"}), 400
            
        # 使用 EmailService 发送邮件
        try:
            success, error = appointment_service.email_service.send_email(
                to_email,
                subject,
                html_content
            )
            
            if success:
                logger.info(f"Email sent successfully to {to_email}")
                return jsonify({"success": True})
            else:
                logger.error(f"Failed to send email: {error}")
                return jsonify({"error": error}), 500
            
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return jsonify({"error": str(e)}), 500
            
    except Exception as e:
        logger.error(f"Error in send_email: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/check_appointments', methods=['POST'])
def check_appointments():
    try:
        data = request.json
        if not data or 'email' not in data:
            logger.warning("Email is required for checking appointments")
            return jsonify({
                "success": False,
                "message": "Please provide an email to search appointments",
                "appointments": []
            }), 400
            
        # 获取并处理邮箱
        user_email = data.get('email', '').lower().strip()
        if not user_email:
            logger.warning("Empty email provided")
            return jsonify({
                "success": False,
                "message": "Email cannot be empty",
                "appointments": []
            }), 400
            
        logger.info(f"Checking appointments for email: {user_email}")
        
        try:
            # 确保数据库连接正确
            conn = appointment_service.get_db_connection()
            if not conn:
                raise Exception("Failed to establish database connection")
                
            cursor = conn.cursor()
            
            # 使用邮箱查询预约，移除 created_at 列
            query = """
                SELECT 
                    a.id,
                    u.name,
                    u.email,
                    u.phone,
                    date(a.appointment_time) as appointment_date,
                    strftime('%H:%M', a.appointment_time) as appointment_time,
                    a.status
                FROM appointments a
                JOIN users u ON a.user_id = u.id
                WHERE LOWER(u.email) = ?
                AND a.status = 'scheduled'
                ORDER BY a.appointment_time DESC
            """
            
            logger.info(f"Executing query: {query} with email: {user_email}")
            cursor.execute(query, (user_email,))
            
            appointments = cursor.fetchall()
            
            if not appointments:
                logger.info(f"No active appointments found for email: {user_email}")
                return jsonify({
                    "success": True,
                    "message": "No active appointments found",
                    "appointments": []
                })
            
            # 转换结果为字典列表
            result = []
            for appointment in appointments:
                try:
                    appointment_dict = {
                        'id': appointment[0],
                        'name': appointment[1],
                        'email': appointment[2],
                        'phone': appointment[3],
                        'date': appointment[4],
                        'time': appointment[5],
                        'status': appointment[6]
                    }
                    result.append(appointment_dict)
                except Exception as e:
                    logger.error(f"Error formatting appointment: {str(e)}")
                    continue
                    
            logger.info(f"Found {len(result)} active appointments for email: {user_email}")
            return jsonify({
                "success": True,
                "message": f"Found {len(result)} active appointments",
                "appointments": result
            })
                
        except sqlite3.Error as e:
            error_msg = f"Database error in check_appointments: {str(e)}"
            logger.error(error_msg)
            return jsonify({
                "success": False,
                "message": error_msg,
                "appointments": []
            }), 500
        finally:
            if 'conn' in locals():
                conn.close()
            
    except Exception as e:
        error_msg = f"Error in check_appointments: {str(e)}"
        logger.error(error_msg)
        return jsonify({
            "success": False,
            "message": error_msg,
            "appointments": []
        }), 500

@app.route('/appointment_history', methods=['POST'])
def get_appointment_history():
    try:
        data = request.json
        if not data or 'email' not in data:
            logger.warning("Email is required for appointment history")
            return jsonify({"success": False, "message": "Email is required"}), 400
            
        user_email = data.get('email', '').lower().strip()
        logger.info(f"Getting appointment history for: {user_email}")
        
        try:
            # Create an instance of AppointmentService
            appointment_service_instance = AppointmentService()
            appointments = appointment_service_instance.get_appointment_history(user_email)
            
            # Format appointments for response
            formatted_appointments = []
            for appt in appointments:
                appt_time = datetime.strptime(appt[0], '%Y-%m-%d %H:%M:%S')
                formatted_appointments.append({
                    'date': appt_time.strftime('%Y-%m-%d'),
                    'time': appt_time.strftime('%H:%M'),
                    'name': appt[1],
                    'email': appt[2],
                    'phone': appt[3],
                    'status': appt[4]
                })
            
            logger.info(f"Found {len(appointments)} appointments in history")
            return jsonify({
                "success": True,
                "appointments": formatted_appointments
            })
        except sqlite3.Error as e:
            logger.error(f"SQLite error in appointment_history: {str(e)}")
            return jsonify({
                "success": False,
                "message": f"Database error: {str(e)}"
            }), 500
            
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error in appointment_history: {error_msg}")
        return jsonify({
            "success": False,
            "message": f"An unexpected error occurred: {error_msg}"
        }), 500

def reset_all_states() -> None:
    """Reset all states to initial values"""
    # 重置服务选择状态
    st.session_state['service_selection_state'] = None
    
    # 重置预约流程状态
    st.session_state['appointment_flow_state'] = None
    
    # 重置取消流程状态
    st.session_state['cancellation_flow_state'] = None
    
    # 重置用户信息
    if 'user_info' in st.session_state:
        del st.session_state['user_info']
    if 'cancel_user_info' in st.session_state:
        del st.session_state['cancel_user_info']
    
    # 重置其他状态
    if 'selected_date' in st.session_state:
        del st.session_state['selected_date']
    if 'selected_time' in st.session_state:
        del st.session_state['selected_time']

def handle_status_check() -> None:
    """Handle appointment status check"""
    st.markdown("### 📋 Your Appointment Status | 您的预约状态")
    
    try:
        result = get_appointment_history(st.session_state['user_info']['email'])
        if result.get('success'):
            formatted_appointments = []
            for appt in result.get('appointments', []):
                appt_time = datetime.strptime(appt[0], '%Y-%m-%d %H:%M:%S')
                formatted_appointments.append({
                    'date': appt_time.strftime('%Y-%m-%d'),
                    'time': appt_time.strftime('%H:%M'),
                    'name': appt[1],
                    'email': appt[2],
                    'phone': appt[3],
                    'status': appt[4]
                })
            display_appointment_history(formatted_appointments)
        else:
            st.error(result.get('message', 'Could not retrieve appointment history'))
    except Exception as e:
        logger.error(f"Error displaying appointment history: {str(e)}")
        st.error("An error occurred while retrieving appointment history")
    
    # 添加返回主菜单按钮
    if st.button("Back to Main Menu | 返回主菜单", use_container_width=True):
        reset_all_states()
        st.rerun()

def handle_appointment_cancellation() -> None:
    """Handles the appointment cancellation workflow"""
    if st.session_state.get('cancellation_flow_state') == 'show_appointments':
        user_info = st.session_state.get('cancel_user_info')
        
        st.markdown("### Your Active Appointments | 您的活跃预约")
        st.info(f"""
        **User Information | 用户信息**
        • Name | 姓名: {user_info['name']}
        • Email | 邮箱: {user_info['email']}
        """)
        
        try:
            # 获取活跃预约
            result = fetch_appointments(user_info['email'], user_info['name'])
            
            if result.get('success'):
                appointments = result.get('appointments', [])
                if appointments:
                    st.success(f"Found {len(appointments)} active appointment(s) | 找到 {len(appointments)} 个活跃预约")
                    
                    for i, appt in enumerate(appointments):
                        with st.container():
                            st.markdown(f"""
                            <div style="padding: 20px; background-color: #f0f7ff; border-radius: 10px; 
                                     margin-bottom: 15px; border: 1px solid #90caf9;">
                                <h4 style="margin-top: 0; color: #1976d2;">Appointment #{i+1} | 预约 #{i+1}</h4>
                                <p><strong>Date | 日期:</strong> {appt['date']}<br>
                                <strong>⏰ Time | 时间:</strong> {appt['time']}</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # 添加取消按钮
                            if st.button("Cancel This Appointment | 取消此预约", 
                                       key=f"cancel_btn_{i}",
                                       type="primary",
                                       use_container_width=True):
                                # 添加用户信息到预约数据
                                appt.update(user_info)
                                cancellation_result = send_cancellation_request(appt)
                                
                                if cancellation_result.get('success'):
                                    st.success("Appointment cancelled successfully | 预约已成功取消")
                                    # 重置状态并返回主聊天界面
                                    reset_all_states()
                                    st.rerun()
                                else:
                                    st.error(f"Failed to cancel appointment: {cancellation_result.get('message', 'Unknown error')}")
                else:
                    st.warning("No active appointments found | 未找到活跃的预约")
                    if st.button("Back to Main Menu | 返回主菜单", use_container_width=True):
                        reset_all_states()
                        st.rerun()
            else:
                st.error(result.get('message', 'Could not retrieve appointments'))
                if st.button("Back to Main Menu | 返回主菜单", use_container_width=True):
                    reset_all_states()
                    st.rerun()
                    
        except Exception as e:
            logger.error(f"Error in appointment cancellation: {str(e)}")
            st.error("An error occurred while fetching your appointments")
            if st.button("Back to Main Menu | 返回主菜单", use_container_width=True):
                reset_all_states()
                st.rerun()

def handle_appointment_scheduling() -> None:
    """Handles the appointment scheduling workflow"""
    if st.session_state.get('service_selection_state') == 'initial':
        # ... 前面的代码保持不变 ...
        
        if st.button("Continue | 继续", type="primary", use_container_width=True):
            if not name or not email:
                st.error("Please enter both your name and email address | 请输入姓名和邮箱")
            else:
                user_info = {
                    'name': name,
                    'email': email,
                    'phone': phone
                }
                
                if "Schedule" in service:
                    st.session_state['user_info'] = user_info
                    st.session_state['appointment_flow_state'] = 'date_selection'
                    st.session_state['service_selection_state'] = 'completed'
                    st.rerun()
    
    elif st.session_state.get('service_selection_state') == 'completed':
        if st.session_state.get('appointment_flow_state') == 'date_selection':
            handle_date_selection()
        elif st.session_state.get('appointment_flow_state') == 'time_selection':
            handle_time_selection()

if __name__ == '__main__':
    logger.info("Starting application...")
    init_db()
    logger.info("Database initialized")
    app.run(debug=True)
   