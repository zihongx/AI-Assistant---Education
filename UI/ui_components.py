import streamlit as st
import pandas as pd
from datetime import datetime, date
import logging
from typing import Dict, List, Union
from enum import Enum

logger = logging.getLogger(__name__)

class AppointmentStatus(str, Enum):
    SCHEDULED = "scheduled"
    CANCELLED = "cancelled"
    COMPLETED = "completed"

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
    
    # 重新初始化必要的状态
    if "messages" not in st.session_state:
        from .ui import get_welcome_message
        st.session_state["messages"] = [
            {"role": "assistant", "content": get_welcome_message()}
        ]
    st.session_state["initialized"] = True
    logger.info("Essential states have been reset")

def display_appointment_history(appointments: List[Dict[str, Union[str, dict]]]) -> None:
    """Display appointment history in a formatted way"""
    if not appointments:
        st.info("No appointment history found | 未找到预约记录")
        return
    
    logger.info(f"Displaying {len(appointments)} appointments")
    
    # Add header
    st.markdown("### 📚 Appointment History | 预约历史")
    
    # Separate active appointments (can be cancelled) from past/cancelled ones
    today = date.today().strftime('%Y-%m-%d')
    active_appointments = []
    inactive_appointments = []
    
    for appt in appointments:
        # Ensure we have all required fields
        if not all(key in appt for key in ['date', 'time', 'status']):
            logger.warning(f"Appointment missing required fields: {appt}")
            continue
            
        if appt['date'] >= today and appt['status'].lower() == AppointmentStatus.SCHEDULED:
            active_appointments.append(appt)
        else:
            inactive_appointments.append(appt)
    
    # Display active appointments first with cancel buttons
    if active_appointments:
        st.markdown("#### Active Appointments | 预约")
        for i, appt in enumerate(active_appointments):
            if display_active_appointment_card(i, appt):
                # If cancel button was clicked, reset relevant states
                st.session_state['cancellation_requested'] = True
                st.session_state['appointment_to_cancel'] = appt
                st.rerun()
    
    # Display history table for all appointments
    st.markdown("#### All Appointments | 历史预约")
    display_appointment_history_table(appointments)
    
    # Add back to main menu button
    if st.button("Back to Main Menu | 返回主界面", key="history_back_btn", use_container_width=True):
        reset_states()
        st.rerun()

def display_active_appointment_card(index, appointment):
    """Display a single active appointment card with cancel button"""
    with st.container():
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"""
            <div style="padding: 15px; background-color: #f0f7ff; border-radius: 10px; margin-bottom: 15px; border: 1px solid #90caf9;">
                <h4 style="margin-top: 0;">Appointment #{index+1} | 预约 #{index+1}</h4>
                <p><strong>Date | 日期:</strong> {appointment['date']}<br>
                <strong>Time | 时间:</strong> {appointment['time']}<br>
                <strong>Status | 状态:</strong> <span style="color:#4CAF50;font-weight:bold;">Active | 活跃</span></p>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            # Add cancel button with unique timestamp key
            cancel_button_key = f"cancel_hist_{index}_{int(datetime.now().timestamp() * 1000)}"
            return st.button("Cancel | 取消", key=cancel_button_key, use_container_width=True, type="primary")

def display_appointment_history_table(appointments):
    """Display a styled table of appointment history"""
    history_data = []
    for appt in appointments:
        # Skip appointments missing required fields
        if not all(key in appt for key in ['date', 'time', 'status']):
            continue
            
        status = appt['status'].lower()
        status_color = "#4CAF50" if status == 'scheduled' else "#F44336"
        status_label = "Active | 活跃" if status == 'scheduled' else "Cancelled | 已取消"
        
        history_data.append({
            "Date | 日期": appt['date'],
            "Time | 时间": appt['time'],
            "Status | 状态": f"<span style='color:{status_color};font-weight:bold;'>{status_label}</span>"
        })
    
    if history_data:
        # Convert to DataFrame for display
        df = pd.DataFrame(history_data)
        st.write(df.to_html(escape=False, index=False), unsafe_allow_html=True)
    else:
        st.info("No appointment history found | 未找到预约记录")

def create_confirmation_message(user_info, date, time):
    """Create the appointment confirmation message"""
    return f"""### 🎉 Appointment Scheduled Successfully!
### 🎉 预约安排成功！

#### 📋 Appointment Details | 预约详情
---
**👤 Personal Information | 个人信息**
• **Name | 姓名:** {user_info['name']}
• **Email | 邮箱:** {user_info['email']}
• **Phone | 电话:** {user_info['phone']}

**📅 Schedule | 时间安排**
• **Date | 日期:** {date}
• **Time | 时间:** {time}

---
📧 A confirmation email has been sent to your email address.
📧 确认邮件已发送至您的邮箱。

**📍 Location | 地址:** 38-08 Union St 12A, NY 11354

⏰ Please arrive 5-10 minutes before your scheduled time. 请提前5-10分钟到达。

**⚠️ Rescheduling Policy | 更改预约政策:**
• To reschedule, please cancel this appointment and book a new one. 如需更改预约时间，请先取消此预约，然后重新预约。

❓ If you have any questions, please contact us at +1 (718)-971-9914. 如有任何问题，请联系我们：+1 (718)-971-9914。

**We look forward to seeing you! 😊 期待与您见面！😊**"""

def create_cancellation_message(user_info: Dict[str, str], date: str, time: str) -> str:
    """
    Create a cancellation confirmation message
    Args:
        user_info: Dictionary containing user information
        date: Appointment date
        time: Appointment time
    Returns:
        Formatted message string
    """
    return f"""
    ✅ Appointment Cancelled Successfully | 预约已成功取消
    
    Dear {user_info['name']},
    
    Your appointment has been successfully cancelled | 您的预约已成功取消:
    • Date | 日期: {date}
    • Time | 时间: {time}
    
    If you would like to schedule a new appointment, please:
    • Call us at +1 (718)-971-9914
    • Email us at newturbony@gmail.com
    • Or visit our website to book online
    
    如果您想重新预约，请：
    • 致电 +1 (718)-971-9914
    • 发送邮件至 newturbony@gmail.com
    • 或访问我们的网站进行在线预约
    
    Thank you for your understanding.
    感谢您的理解。
    """

def get_welcome_message():
    """Get the welcome message for new users"""
    return """👋 **Welcome to New Turbo Education!**

I'm your AI assistant, here to help you with:

📅 **Appointments**
• Schedule new appointments
• Cancel existing appointments
• Check appointment status

📚 **Courses & Programs**
• SAT, AP, ACT, SHSAT preparation
• TOEFL & ESL programs
• College admissions consulting

💰 **Pricing & Information**
• Course fees
• Program details
• General inquiries

How can I assist you today?

---

👋 **欢迎来到新突破教育！**

我是您的AI助手，可以帮您：

📅 **预约服务**
• 预约新课程
• 取消现有预约
• 查询预约状态

📚 **课程与项目**
• SAT、AP、ACT、SHSAT备考
• TOEFL和ESL项目
• 大学申请咨询

💰 **价格与信息**
• 课程费用
• 项目详情
• 一般咨询

今天我能为您提供什么帮助？"""

def get_custom_css():
    """Get custom CSS for styling the UI"""
    return """
<style>
    /* Main container styling */
    .main {
        padding: 2rem;
    }
    
    /* Chat container styling */
    #message-container {
        overflow-y: scroll;
        max-height: 600px;
        -ms-overflow-style: none;
        scrollbar-width: none;
        padding: 1rem;
        background-color: #f8f9fa;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
    
    /* Hide scrollbar */
    #message-container::-webkit-scrollbar {
        display: none;
    }
    
    /* Message bubbles */
    .stChatMessage {
        padding: 1rem;
        margin-bottom: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    /* Form styling */
    .stForm {
        background-color: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 1rem 0;
    }
    
    /* Button styling */
    .stButton>button {
        background-color: #1f77b4;
        color: white;
        border: none;
        border-radius: 5px;
        padding: 0.5rem 1rem;
        transition: background-color 0.3s;
    }
    
    .stButton>button:hover {
        background-color: #1565c0;
    }
    
    /* Input field styling */
    .stTextInput>div>div>input {
        border-radius: 5px;
        border: 1px solid #ddd;
        padding: 0.5rem;
    }
    
    /* Status indicators */
    .status-indicator {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-right: 5px;
    }
    
    .status-scheduled {
        background-color: #4caf50;
    }
    
    .status-canceled {
        background-color: #f44336;
    }
</style>
""" 