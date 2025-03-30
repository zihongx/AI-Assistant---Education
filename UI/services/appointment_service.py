import requests
import logging
from datetime import datetime, date, timedelta
import os
from dotenv import load_dotenv
from typing import Dict, List, Optional, Union
import sqlite3
import streamlit as st

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
_ = load_dotenv()
API_URL = os.getenv("API_URL", "http://127.0.0.1:5000")
API_TIMEOUT = 15  # 统一的API超时设置（秒）
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@example.com")

# 预约状态常量
class AppointmentStatus:
    SCHEDULED = 'scheduled'
    CANCELLED = 'canceled'
    COMPLETED = 'completed'
    
def _handle_api_response(response: requests.Response) -> Dict[str, Union[bool, str, List]]:
    """Helper function to handle API responses consistently"""
    try:
        if response.status_code == 200:
            result = response.json()
            return {
                'success': result.get('success', False),
                'message': result.get('message', 'Operation completed successfully'),
                'appointments': result.get('appointments', []),
                'available_slots': result.get('available_slots', [])
            }
        else:
            error_message = "No matching appointment found" if response.status_code == 404 else f"HTTP Error: {response.status_code} - {response.reason}"
            return {
                'success': False,
                'message': error_message
            }
    except ValueError as e:
        logger.error(f"Error parsing API response: {str(e)}")
        return {
            'success': False,
            'message': f"Error parsing response: {str(e)}"
        }

def fetch_appointments(email: str) -> Dict[str, Union[bool, str, List]]:
    """
    Fetches appointments from the API with improved error handling
    Args:
        email (str): User's email address
    Returns:
        Dict with success status, message and appointments list
    """
    try:
        if not email:
            logger.warning("No email provided for appointment search")
            return {
                'success': False,
                'message': "Please provide an email to search appointments",
                'appointments': []
            }
            
        # 构建请求数据，只使用邮箱
        request_data = {
            "email": email.strip().lower(),
            "status": AppointmentStatus.SCHEDULED  # 只查询已预约的状态
        }
            
        logger.info(f"Fetching appointments for email: {email}")
        
        try:
            response = requests.post(
                f"{API_URL}/check_appointments",
                json=request_data,
                timeout=API_TIMEOUT
            )
            
            logger.info(f"API response status: {response.status_code}")
            logger.info(f"API response content: {response.text[:500]}")
            
            if response.status_code == 200:
                result = response.json()
                appointments = result.get('appointments', [])
                
                # 过滤出已预约的预约
                active_appointments = [
                    appt for appt in appointments 
                    if appt.get('status') == AppointmentStatus.SCHEDULED
                ]
                
                if not active_appointments:
                    logger.info("No active appointments found")
                    return {
                        'success': True,
                        'message': "No active appointments found",
                        'appointments': []
                    }
                
                logger.info(f"Found {len(active_appointments)} active appointments")
                return {
                    'success': True,
                    'message': f"Found {len(active_appointments)} active appointments",
                    'appointments': active_appointments
                }
            else:
                error_msg = f"Server error: {response.status_code}"
                logger.error(error_msg)
                logger.error(f"Response content: {response.text[:500]}")
                return {
                    'success': False,
                    'message': error_msg,
                    'appointments': []
                }
                
        except requests.exceptions.Timeout:
            logger.error("Request timed out when fetching appointments")
            return {
                'success': False,
                'message': "Request timed out. The server is taking too long to respond.",
                'appointments': []
            }
        except requests.exceptions.ConnectionError:
            logger.error("Connection error when fetching appointments")
            return {
                'success': False,
                'message': "Could not connect to the server. Please try again later.",
                'appointments': []
            }
            
    except Exception as e:
        logger.error(f"Unexpected error fetching appointments: {str(e)}")
        return {
            'success': False,
            'message': f"An unexpected error occurred: {str(e)}",
            'appointments': []
        }

def send_cancellation_request(appointment_data: Dict[str, str]) -> Dict[str, Union[bool, str]]:
    """
    Send the cancellation request to the API and return result
    Args:
        appointment_data: Dictionary containing email, date, time, name, and phone
    Returns:
        Dict with success status and message
    """
    try:
        # 验证必需的字段
        required_fields = ['email', 'date', 'time', 'name']
        for field in required_fields:
            if not appointment_data.get(field):
                logger.error(f"Missing required field: {field}")
                return {
                    'success': False,
                    'message': f"Missing required field: {field}"
                }
        
        logger.info(f"Sending cancellation request for appointment on {appointment_data['date']} at {appointment_data['time']}")
        
        # 构建请求数据，确保所有必需字段都存在
        request_data = {
            "email": appointment_data['email'].strip(),
            "date": appointment_data['date'],
            "time": appointment_data['time'],
            "name": appointment_data['name'],
            "phone": appointment_data.get('phone', '')
        }
        
        response = requests.post(
            f"{API_URL}/cancel_appointment",
            json=request_data,
            timeout=API_TIMEOUT
        )
        
        logger.info(f"API Response Status: {response.status_code}")
        logger.info(f"API Response Content: {response.text[:500]}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                # 发送邮件通知
                try:
                    # 发送给用户的取消确认邮件
                    user_email_data = {
                        'to_email': appointment_data['email'],
                        'subject': 'Appointment Cancellation Confirmation | 预约取消确认',
                        'template': 'cancellation_confirmation',
                        'data': {
                            'name': appointment_data['name'],
                            'date': appointment_data['date'],
                            'time': appointment_data['time']
                        }
                    }
                    
                    # 发送给管理员的取消通知邮件
                    admin_email_data = {
                        'to_email': ADMIN_EMAIL,
                        'subject': 'Appointment Cancellation Notification | 预约取消通知',
                        'template': 'cancellation_notification',
                        'data': {
                            'name': appointment_data['name'],
                            'email': appointment_data['email'],
                            'phone': appointment_data.get('phone', 'N/A'),
                            'date': appointment_data['date'],
                            'time': appointment_data['time']
                        }
                    }
                    
                    # 发送邮件
                    response = requests.post(
                        f"{API_URL}/send_email",
                        json=user_email_data,
                        timeout=API_TIMEOUT
                    )
                    
                    if response.status_code != 200:
                        logger.warning(f"Failed to send user cancellation email: {response.text}")
                    
                    response = requests.post(
                        f"{API_URL}/send_email",
                        json=admin_email_data,
                        timeout=API_TIMEOUT
                    )
                    
                    if response.status_code != 200:
                        logger.warning(f"Failed to send admin cancellation email: {response.text}")
                        
                except Exception as e:
                    logger.error(f"Error sending cancellation emails: {str(e)}")
                    # 不中断流程，继续返回成功状态
                
                return {
                    'success': True,
                    'message': 'Appointment cancelled successfully',
                    'date': appointment_data['date'],
                    'time': appointment_data['time']
                }
            else:
                return {
                    'success': False,
                    'message': result.get('message', 'Failed to cancel appointment')
                }
        else:
            return {
                'success': False,
                'message': f"Server error: {response.status_code}"
            }
    
    except requests.exceptions.Timeout:
        logger.error("API request timed out")
        return {
            'success': False,
            'message': "Request timed out. Server is taking too long to respond."
        }
    
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error: {str(e)}")
        return {
            'success': False,
            'message': f"Connection error: {str(e)}"
        }
    
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {
            'success': False,
            'message': f"Unexpected error: {str(e)}"
        }

def check_availability(date: str) -> Dict[str, Union[bool, str, List]]:
    """Check available time slots for a given date"""
    try:
        logger.info(f"Checking availability for date: {date}")
        response = requests.post(
            f"{API_URL}/schedule",
            json={"action": "check_availability", "date": date},
            timeout=API_TIMEOUT
        )
        
        logger.info(f"API Response Status: {response.status_code}")
        return _handle_api_response(response)
        
    except requests.exceptions.Timeout:
        logger.error("Request timed out when checking availability")
        return {
            'success': False,
            'message': "Request timed out. The server is taking too long to respond."
        }
    except requests.exceptions.ConnectionError:
        logger.error("Connection error when checking availability")
        return {
            'success': False,
            'message': "Could not connect to the server. Please try again later."
        }
    except Exception as e:
        logger.error(f"Error checking availability: {str(e)}")
        return {
            'success': False,
            'message': str(e)
        }

def schedule_appointment(user_info: Dict[str, str], date: str, time: str) -> Dict[str, Union[bool, str]]:
    """Schedule a new appointment"""
    try:
        logger.info(f"Scheduling appointment for {user_info['email']} on {date} at {time}")
        response = requests.post(
            f"{API_URL}/schedule",
            json={
                "action": "book_appointment",
                "name": user_info['name'],
                "email": user_info['email'],
                "phone": user_info.get('phone', ''),
                "date": date,
                "time": time
            },
            timeout=API_TIMEOUT
        )
        
        logger.info(f"API Response Status: {response.status_code}")
        return _handle_api_response(response)
        
    except requests.exceptions.Timeout:
        logger.error("Request timed out when scheduling appointment")
        return {
            'success': False,
            'message': "Request timed out. The server is taking too long to respond."
        }
    except requests.exceptions.ConnectionError:
        logger.error("Connection error when scheduling appointment")
        return {
            'success': False,
            'message': "Could not connect to the server. Please try again later."
        }
    except Exception as e:
        logger.error(f"Error scheduling appointment: {str(e)}")
        return {
            'success': False,
            'message': str(e)
        }

def get_appointment_history(email: str) -> Dict[str, Union[bool, str, List]]:
    """
    Get appointment history for a user from the API
    
    Args:
        email: User's email address
        
    Returns:
        Dict with success status, message and appointments list
    """
    try:
        if not email:
            logger.warning("No email provided for appointment history")
            return {
                'success': False,
                'message': "Please provide an email to view appointment history",
                'appointments': []
            }
        
        request_data = {
            "email": email.strip().lower()
        }
        
        logger.info(f"Fetching appointment history for email: {email}")
        
        try:
            response = requests.post(
                f"{API_URL}/appointment_history",
                json=request_data,
                timeout=API_TIMEOUT
            )
            
            logger.info(f"API response status: {response.status_code}")
            logger.info(f"API response content: {response.text[:500]}")
            
            return _handle_api_response(response)
                
        except requests.exceptions.Timeout:
            logger.error("Request timed out when fetching appointment history")
            return {
                'success': False,
                'message': "Request timed out. The server is taking too long to respond.",
                'appointments': []
            }
        except requests.exceptions.ConnectionError:
            logger.error("Connection error when fetching appointment history")
            return {
                'success': False,
                'message': "Could not connect to the server. Please try again later.",
                'appointments': []
            }
            
    except Exception as e:
        logger.error(f"Unexpected error fetching appointment history: {str(e)}")
        return {
            'success': False,
            'message': f"An unexpected error occurred: {str(e)}",
            'appointments': []
        }

def handle_appointment_scheduling() -> None:
    """Handles the appointment scheduling workflow"""
    logger.info("Handling appointment request")
    
    # 初始化服务选择状态
    if not st.session_state.get('service_selection_state'):
        st.session_state['service_selection_state'] = 'initial'
    
    # 服务选择界面
    if st.session_state.get('service_selection_state') == 'initial':
        st.markdown("### 👤 Your Information | 您的信息")
        
        # 用户信息表单
        name = st.text_input("Full Name | 姓名", placeholder="Enter your full name | 请输入您的姓名")
        email = st.text_input("Email Address | 邮箱", placeholder="Enter your email address | 请输入您的邮箱")
        phone = st.text_input("Phone Number | 电话", placeholder="Enter your phone number | 请输入您的电话号码")
        
        st.markdown("### 🎯 Select Service | 选择服务")
        
        # 服务选择
        service = st.radio(
            "What would you like to do? | 您想要进行什么操作？",
            options=[
                "Schedule a new appointment | 预约新课程",
                "Cancel an existing appointment | 取消现有预约",
                "Check appointment status | 查询预约状态"
            ],
            key="service_selection"
        )
        
        # 继续按钮
        if st.button("Continue | 继续", type="primary", use_container_width=True):
            if not name or not email:
                st.error("Please enter both your name and email address | 请输入姓名和邮箱")
            else:
                # 存储用户信息
                user_info = {
                    'name': name,
                    'email': email,
                    'phone': phone
                }
                
                # 根据选择的服务设置相应的状态
                if "Schedule" in service:
                    st.session_state['user_info'] = user_info
                    st.session_state['appointment_flow_state'] = 'date_selection'
                    st.session_state['service_selection_state'] = 'completed'
                elif "Cancel" in service:
                    st.session_state['cancel_user_info'] = user_info
                    st.session_state['cancellation_flow_state'] = 'show_appointments'
                    st.session_state['service_selection_state'] = 'completed'
                else:  # Check appointment status
                    st.session_state['user_info'] = user_info
                    st.session_state['appointment_flow_state'] = 'status_check'
                    st.session_state['service_selection_state'] = 'completed'
                
                st.rerun()
    
    # 处理不同的服务流程
    elif st.session_state.get('service_selection_state') == 'completed':
        if st.session_state.get('appointment_flow_state') == 'date_selection':
            handle_date_selection()
        elif st.session_state.get('appointment_flow_state') == 'time_selection':
            handle_time_selection()
        elif st.session_state.get('appointment_flow_state') == 'status_check':
            handle_status_check()
        elif st.session_state.get('cancellation_flow_state') == 'show_appointments':
            handle_appointment_cancellation()

def handle_status_check() -> None:
    """Handle appointment status check"""
    st.markdown("### 📋 Your Appointment Status | 您的预约状态")
    
    try:
        result = get_appointment_history(st.session_state['user_info']['email'])
        if result.get('success'):
            appointments = result.get('appointments', [])
            if appointments:
                # 使用相同的显示函数来保持一致性
                display_appointment_history(appointments)
            else:
                st.info("No appointments found | 未找到预约记录")
        else:
            st.error(result.get('message', 'Could not retrieve appointment history'))
    except Exception as e:
        logger.error(f"Error displaying appointment history: {str(e)}")
        st.error("An error occurred while retrieving appointment history")
    
    # 添加返回按钮
    if st.button("Back to Main Menu | 返回主菜单", use_container_width=True):
        reset_states()
        st.rerun()

def display_appointment_history(appointments: List[Dict]) -> None:
    """Display appointment history in a formatted way"""
    if not appointments:
        st.info("No appointment history found | 没有找到预约历史")
        return
    
    st.success(f"Found {len(appointments)} appointment(s) | 找到 {len(appointments)} 个预约")
    
    # 定义状态显示样式
    status_styles = {
        AppointmentStatus.SCHEDULED: "background-color: #e8f5e9; border-color: #81c784; color: #2e7d32",  # 绿色主题
        AppointmentStatus.CANCELLED: "background-color: #ffebee; border-color: #e57373; color: #c62828",  # 红色主题
        AppointmentStatus.COMPLETED: "background-color: #e3f2fd; border-color: #64b5f6; color: #1565c0"   # 蓝色主题
    }
    
    # 定义状态中文翻译
    status_translations = {
        AppointmentStatus.SCHEDULED: "已预约 | Scheduled",
        AppointmentStatus.CANCELLED: "已取消 | Cancelled",
        AppointmentStatus.COMPLETED: "已完成 | Completed"
    }
    
    for appt in appointments:
        status = appt.get('status', AppointmentStatus.SCHEDULED)
        style = status_styles.get(status, status_styles[AppointmentStatus.SCHEDULED])
        status_text = status_translations.get(status, status)
        
        with st.container():
            st.markdown(f"""
            <div style="padding: 20px; {style}; border-radius: 10px; 
                     margin-bottom: 15px; border: 1px solid;">
                <h4 style="margin-top: 0;">Appointment Details | 预约详情</h4>
                <p>
                    <strong>📅 Date | 日期:</strong> {appt['date']}<br>
                    <strong>⏰ Time | 时间:</strong> {appt['time']}<br>
                    <strong>👤 Name | 姓名:</strong> {appt['name']}<br>
                    <strong>📱 Phone | 电话:</strong> {appt.get('phone', 'N/A')}<br>
                    <strong>📊 Status | 状态:</strong> {status_text}
                </p>
            </div>
            """, unsafe_allow_html=True)

def reset_states() -> None:
    """Reset essential states"""
    states_to_clear = [
        'service_selection_state',
        'appointment_flow_state',
        'cancellation_flow_state',
        'user_info',
        'cancel_user_info',
        'selected_date',
        'selected_time',
        'selected_appointment_date',
        'cancellation_requested',
        'appointment_to_cancel'
    ]
    for state in states_to_clear:
        if state in st.session_state:
            del st.session_state[state]
    logger.info("Essential states have been reset") 