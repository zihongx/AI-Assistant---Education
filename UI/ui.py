import streamlit as st
import requests
import logging
from datetime import datetime, timedelta, date
import os
from dotenv import load_dotenv
import pandas as pd
from typing import Dict, List, Optional, Union
from services.appointment_service import (
    fetch_appointments,
    send_cancellation_request,
    check_availability,
    schedule_appointment,
    get_appointment_history,
    reset_states as reset_service_states
)
from services.message_service import process_message
from ui_components import (
    display_appointment_history,
    create_confirmation_message,
    create_cancellation_message,
    get_welcome_message,
    get_custom_css,
    reset_states as reset_ui_states
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
_ = load_dotenv()
API_URL = os.getenv("API_URL", "http://127.0.0.1:5000")

logger.info(f"API URL set to: {API_URL}")

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
        name = st.text_input("Full Name | 姓名", 
                           key="scheduling_name_input",
                           placeholder="Enter your full name | 请输入您的姓名")
        email = st.text_input("Email Address | 邮箱", 
                            key="scheduling_email_input",
                            placeholder="Enter your email address | 请输入您的邮箱")
        phone = st.text_input("Phone Number | 电话", 
                            key="scheduling_phone_input",
                            placeholder="Enter your phone number | 请输入您的电话号码")
        
        st.markdown("### 🎯 Select Service | 选择服务")
        
        # 服务选择
        service = st.radio(
            "What would you like to do? | 您想要进行什么操作？",
            options=[
                "Schedule a new appointment | 预约新课程",
                "Cancel an existing appointment | 取消现有预约",
                "Check appointment status | 查询预约状态"
            ],
            key="service_selection_radio"
        )
        
        # 继续按钮
        if st.button("Continue | 继续", 
                    key="service_continue_btn",
                    type="primary", 
                    use_container_width=True):
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

def handle_date_selection() -> None:
    """Handle the date selection step of appointment scheduling"""
    logger.info("Inside handle_date_selection")
    st.markdown("### 📅 Select Appointment Date | 选择预约日期")
    
    # Get today's date
    today = datetime.now().date()
    # Only allow dates up to 3 months in the future
    max_date = today + timedelta(days=90)
    
    # Use the current selection if available, otherwise default to today
    selected_date = st.date_input(
        "Select your preferred date | 选择您偏好的日期",
        min_value=today,
        max_value=max_date,
        value=st.session_state.get('selected_appointment_date', today),
        key="date_selection_input"
    )
    
    logger.info(f"Selected date: {selected_date}")
    
    # Store the selected date in session state for persistence
    st.session_state['selected_appointment_date'] = selected_date
    
    # Continue buttons - horizontal layout
    col1, col2 = st.columns([1, 4])
    with col2:
        col2_1, col2_2 = st.columns([1, 1])
        with col2_1:
            if st.button("Back | 返回", key="date_back_btn", use_container_width=True):
                st.session_state['appointment_flow_state'] = 'user_info'
                st.rerun()
        with col2_2:
            if st.button("Continue | 继续", key="date_continue_btn", use_container_width=True, type="primary"):
                if selected_date:
                    st.session_state['selected_date'] = selected_date.strftime('%Y-%m-%d')
                    logger.info(f"Selected date: {st.session_state['selected_date']}")
                    st.session_state['appointment_flow_state'] = 'time_selection'
                    st.rerun()
                else:
                    st.error("Please select a date before continuing | 请先选择日期")

def handle_time_selection() -> None:
    """Handle the time selection step of appointment scheduling"""
    st.markdown("### ⏰ Select Appointment Time | 选择预约时间")
    st.markdown(f"**Selected Date | 已选日期:** {st.session_state['selected_date']}")
    
    try:
        # Check availability
        with st.spinner("Loading available time slots... | 正在加载可用时间段..."):
            logger.info(f"Checking availability for date: {st.session_state['selected_date']}")
            result = check_availability(st.session_state['selected_date'])
            logger.info(f"Availability check result: {result}")
            
            # Get available slots regardless of success flag if they exist
            available_slots = result.get('available_slots', [])
            
            if not available_slots:
                st.warning("No available slots for the selected date. Please try another date. | 所选日期没有可用时间段，请尝试其他日期。")
                if st.button("Back to Date Selection | 返回日期选择", key="time_back_no_slots_btn", use_container_width=True):
                    st.session_state['appointment_flow_state'] = 'date_selection'
                    st.rerun()
            else:
                # Show success message with available slots count
                st.success(f"Found {len(available_slots)} available time slots | 找到 {len(available_slots)} 个可用时间段")
                
                # Create time slot selection
                selected_time = st.selectbox(
                    "Choose a time slot | 选择时间段",
                    options=available_slots,
                    key="time_selection_input"
                )
                
                # Add buttons in columns
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Back | 返回", key="time_back_btn", use_container_width=True):
                        st.session_state['appointment_flow_state'] = 'date_selection'
                        st.rerun()
                with col2:
                    if st.button("Schedule Appointment | 确认预约", key="time_schedule_btn", use_container_width=True, type="primary"):
                        if selected_time:
                            # Store the selected time
                            st.session_state['selected_time'] = selected_time
                            
                            # Get user info from session state
                            user_info = st.session_state['user_info']
                            
                            # Schedule the appointment
                            schedule_result = schedule_appointment(
                                user_info,
                                st.session_state['selected_date'],
                                selected_time
                            )
                            
                            if schedule_result.get('success'):
                                # Create confirmation message
                                confirmation_msg = create_confirmation_message(
                                    user_info,
                                    st.session_state['selected_date'],
                                    selected_time
                                )
                                
                                # Add to chat history
                                st.session_state["messages"].append(
                                    {"role": "assistant", "content": confirmation_msg}
                                )
                                
                                # Reset states
                                reset_scheduling_state()
                                st.rerun()
                            else:
                                st.error(f"Failed to schedule appointment: {schedule_result.get('message', 'Unknown error')}")
                        else:
                            st.error("Please select a time slot before continuing | 请先选择时间段")
    except Exception as e:
        logger.error(f"Error in time selection: {str(e)}")
        st.error(f"An error occurred while loading time slots: {str(e)}")
        if st.button("Back to Date Selection | 返回日期选择", key="time_back_error_btn", use_container_width=True):
            st.session_state['appointment_flow_state'] = 'date_selection'
            st.rerun()

def reset_scheduling_state() -> None:
    """Reset all scheduling-related state variables"""
    logger.info("Resetting all scheduling state variables")
    
    # Reset state indicators
    st.session_state['appointment_flow_state'] = None
    
    # Reset date/time selections
    st.session_state['selected_date'] = None
    st.session_state['selected_time'] = None
    st.session_state['selected_appointment_date'] = None
    
    # Reset user info
    if 'user_info' in st.session_state:
        del st.session_state['user_info']
    
    # Reset any other stored data
    if 'available_slots' in st.session_state:
        del st.session_state['available_slots']

def handle_appointment_cancellation() -> None:
    """Handles the appointment cancellation workflow"""
    if st.session_state.get('cancellation_flow_state') == 'show_appointments':
        user_info = st.session_state.get('cancel_user_info')
        
        if not user_info:
            st.error("User information not found. Please try again.")
            if st.button("Finish | 结束", key="cancel_finish_no_info", use_container_width=True):
                reset_scheduling_state()
                st.session_state['service_selection_state'] = None
                st.rerun()
            return
            
        st.markdown("### Your Active Appointments | 您的预约")
        st.info(f"""
        **User Information | 用户信息**
        • Name | 姓名: {user_info['name']}
        • Email | 邮箱: {user_info['email']}
        """)
        
        try:
            # 只使用邮箱查找预约
            result = fetch_appointments(user_info['email'])
            
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
                                <p><strong>📅 Date | 日期:</strong> {appt.get('date', 'N/A')}<br>
                                <strong>⏰ Time | 时间:</strong> {appt.get('time', 'N/A')}</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            if st.button("Cancel This Appointment | 取消此预约", 
                                       key=f"cancel_appointment_btn_{i}",
                                       type="primary",
                                       use_container_width=True):
                                # 只发送必要的取消数据
                                cancel_data = {
                                    'email': user_info['email'],
                                    'date': appt.get('date'),
                                    'time': appt.get('time'),
                                    'name': user_info['name'],
                                    'phone': user_info.get('phone', '')
                                }
                                cancellation_result = send_cancellation_request(cancel_data)
                                
                                if cancellation_result.get('success'):
                                    # 创建取消确认消息
                                    cancellation_msg = create_cancellation_message(
                                        user_info,
                                        appt.get('date'),
                                        appt.get('time')
                                    )
                                    
                                    # 添加到聊天历史
                                    st.session_state["messages"].append({
                                        "role": "assistant", 
                                        "content": cancellation_msg
                                    })
                                    
                                    # 显示成功消息
                                    st.success("""
                                    ✅ Appointment cancelled successfully | 预约已成功取消
                                    
                                    A confirmation email has been sent to your email address.
                                    确认邮件已发送到您的邮箱。
                                    """)
                                    
                                    # Reset states and close the cancellation interface
                                    st.session_state['service_selection_state'] = None
                                    st.session_state['cancellation_flow_state'] = None
                                    st.session_state['cancel_user_info'] = None
                                    st.rerun()
                                else:
                                    st.error(f"Failed to cancel appointment: {cancellation_result.get('message', 'Unknown error')}")
                else:
                    st.warning("No active appointments found | 未找到活跃的预约")
                    if st.button("Finish | 结束", key="cancel_finish_no_appointments", use_container_width=True):
                        st.session_state["messages"].append({
                            "role": "assistant", 
                            "content": "No active appointments found. Is there anything else I can help you with? | 未找到活跃的预约。还有什么我可以帮您的吗？"
                        })
                        st.session_state['service_selection_state'] = None
                        st.session_state['cancellation_flow_state'] = None
                        st.session_state['cancel_user_info'] = None
                        st.rerun()
            else:
                st.error(result.get('message', 'Could not retrieve appointments'))
                if st.button("Finish | 结束", key="cancel_finish_error", use_container_width=True):
                    st.session_state["messages"].append({
                        "role": "assistant", 
                        "content": "Sorry, there was an error retrieving your appointments. Please try again later. | 抱歉，获取预约时出现错误。请稍后再试。"
                    })
                    st.session_state['service_selection_state'] = None
                    st.session_state['cancellation_flow_state'] = None
                    st.session_state['cancel_user_info'] = None
                    st.rerun()
                    
        except Exception as e:
            logger.error(f"Error in appointment cancellation: {str(e)}")
            st.error("An error occurred while fetching your appointments")
            if st.button("Finish | 结束", key="cancel_finish_exception", use_container_width=True):
                st.session_state["messages"].append({
                    "role": "assistant", 
                    "content": "Sorry, an error occurred. Please try again later. | 抱歉，发生错误。请稍后再试。"
                })
                st.session_state['service_selection_state'] = None
                st.session_state['cancellation_flow_state'] = None
                st.session_state['cancel_user_info'] = None
                st.rerun()

def handle_status_check() -> None:
    """Handle appointment status check"""
    st.markdown("### 📋 Your Appointment Status | 您的预约状态")
    
    try:
        result = get_appointment_history(st.session_state['user_info']['email'])
        if result.get('success'):
            appointments = result.get('appointments', [])
            if appointments:
                display_appointment_history(appointments)
            else:
                st.info("No appointments found | 未找到预约记录")
        else:
            st.error(result.get('message', 'Could not retrieve appointment history'))
    except Exception as e:
        logger.error(f"Error displaying appointment history: {str(e)}")
        st.error("An error occurred while retrieving appointment history")
    
    # Add back to main menu button
    if st.button("Back to Main Menu | 返回主菜单", key="status_back_btn", use_container_width=True):
        reset_all_states()
        st.rerun()

# Initialize session state for chat history
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# Initialize appointment flow state
if "appointment_flow_state" not in st.session_state:
    st.session_state["appointment_flow_state"] = None

# Initialize loading state
if "thinking" not in st.session_state:
    st.session_state["thinking"] = False

# Initialize welcome message
if "initialized" not in st.session_state:
    st.session_state["messages"] = [
        {"role": "assistant", "content": get_welcome_message()}
    ]
    st.session_state["initialized"] = True

# Add custom CSS for better UI
st.markdown(get_custom_css(), unsafe_allow_html=True)

# Streamlit App - Chat UI
st.title("🤖 New Turbo Education AI Assistant")

# Create a container for messages with auto-scroll
chat_container = st.container()

# Display chat history and forms
with chat_container:
    for msg in st.session_state["messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    
    # Display forms after chat history
    if st.session_state.get('service_selection_state') == 'initial':
        handle_appointment_scheduling()
    elif st.session_state.get('service_selection_state') == 'completed':
        if st.session_state.get('cancellation_flow_state') == 'show_appointments':
            handle_appointment_cancellation()
        elif st.session_state.get('appointment_flow_state') == 'date_selection':
            handle_date_selection()
        elif st.session_state.get('appointment_flow_state') == 'time_selection':
            handle_time_selection()
        elif st.session_state.get('appointment_flow_state') == 'status_check':
            handle_status_check()
    
    # Show loading message if thinking
    if st.session_state["thinking"]:
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                st.empty()

    # User input field with placeholder
    if user_input := st.chat_input("Type your message here...", key="user_input"):
        logger.info(f"Received user input: {user_input[:30]}...")
        # Add user message to chat history immediately
        st.session_state["messages"].append({"role": "user", "content": user_input})
        st.session_state["thinking"] = True
        st.rerun()

# Process any pending message first (before displaying)
if st.session_state["thinking"]:
    try:
        last_message = st.session_state["messages"][-1]["content"]
        logger.info(f"Processing user message: {last_message[:30]}...")
        
        # Process the message
        result = process_message(
            last_message,
            st.session_state["messages"][-5:] if len(st.session_state["messages"]) > 1 else []
        )
        
        if result['success']:
            chatbot_reply = result['response']
            
            # Handle appointment-related intents
            if result['is_appointment_intent']:
                logger.info("Detected appointment-related intent")
                st.session_state['service_selection_state'] = 'initial'
                chatbot_reply = """I'll help you with your appointment. Please provide your information and select what you'd like to do below:
我将帮您处理预约事宜。请在下方提供您的信息并选择您想进行的操作："""
        else:
            chatbot_reply = result['message']
            
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        chatbot_reply = f"⚠️ **Error**\n\nI encountered an error: {str(e)}\n\nPlease try again."

    # Add assistant's response to chat history
    logger.info("Adding assistant response to chat history")
    st.session_state["messages"].append({"role": "assistant", "content": chatbot_reply})
    st.session_state["thinking"] = False
    st.rerun()

def cancel_appointment(appt: Dict[str, str]) -> bool:
    """Handle the cancellation of an appointment"""
    try:
        logger.info(f"Cancelling appointment for {appt['email']} on {appt['date']} at {appt['time']}")
        
        # Use the service function instead of direct API call
        result = send_cancellation_request(appt)
        
        if result.get('success'):
            logger.info("Appointment cancelled successfully")
            st.session_state['cancellation_success'] = True
            return True
        else:
            logger.warning(f"Failed to cancel appointment: {result.get('message')}")
            st.error(f"Failed to cancel appointment: {result.get('message', 'Unknown error')}")
            return False
            
    except Exception as e:
        logger.error(f"Error cancelling appointment: {str(e)}")
        st.error(f"Error cancelling appointment: {str(e)}")
        return False

def reset_all_states() -> None:
    """Reset all states to initial values"""
    # 调用其他模块的状态重置函数
    reset_service_states()
    # 重置UI状态
    reset_ui_states()
    
    # 重置其他状态
    states_to_clear = [
        'thinking',
        'form_submitted',
        'form_data',
        'cancel_form_data',
        'available_slots'
    ]
    
    for state in states_to_clear:
        if state in st.session_state:
            del st.session_state[state]
    
    # 重新初始化必要的状态
    st.session_state["messages"] = [
        {"role": "assistant", "content": get_welcome_message()}
    ]
    st.session_state["initialized"] = True
    
    logger.info("All states have been reset")
