import streamlit as st
import requests
import os
from dotenv import load_dotenv
import datetime

load_dotenv()

API_URL = os.getenv('API_URL', 'http://127.0.0.1:5000')

def display_appointment_history(email: str):
    try:
        with st.spinner("Loading appointment history..."):
            response = requests.post(
                f"{API_URL}/appointment_history",
                json={"email": email}
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get('success'):
                appointments = result.get('appointments', [])
                if not appointments:
                    st.info("No appointment history found.")
                else:
                    st.markdown("### 📋 Appointment History")
                    for appt in appointments:
                        status_color = "🟢" if appt['status'] == 'scheduled' else "🔴"
                        st.markdown(f"""
                        {status_color} **Date:** {appt['date']}  
                        **Time:** {appt['time']}  
                        **Status:** {appt['status'].title()}
                        """)
            else:
                st.error(result.get('message', "Failed to fetch appointment history"))
    except requests.exceptions.ConnectionError:
        st.error("Could not connect to the server. Please make sure the server is running.")
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching appointment history: {str(e)}")

def handle_appointment_cancellation():
    st.markdown("### ❌ Cancel Appointment")
    
    # Show helpful message at the top
    st.info("""
    To cancel your appointment:
    1. Enter your email address below
    2. Click "Check Appointments" to view your active appointments
    3. Use the "Cancel" button next to the appointment you want to cancel
    """)
    
    col1, col2 = st.columns([6, 1])
    with col1:
        email = st.text_input("Email", key="cancel_email", placeholder="Enter your email address")
    with col2:
        if st.button("Clear", key="clear_cancellation"):
            st.session_state['cancellation_state'] = None
            st.session_state['appointments'] = None
            st.rerun()
    
    # Add a note about required information
    if not email:
        st.warning("Please enter your email address to view your appointments.")
            
    if email and st.button("Check Appointments", use_container_width=True):
        try:
            with st.spinner("Checking your appointments..."):
                response = requests.post(
                    f"{API_URL}/check_appointments",
                    json={"email": email}
                )
                response.raise_for_status()
                result = response.json()
                
                if result.get('success'):
                    appointments = result.get('appointments', [])
                    if not appointments:
                        st.warning("No active appointments found for this email. Please make sure you've entered the correct email address.")
                        # Add suggestion for scheduling
                        st.info("Would you like to schedule a new appointment? Just type 'schedule appointment' in the chat.")
                        st.session_state['appointments'] = None
                    else:
                        st.session_state['appointments'] = appointments
                        st.rerun()
                else:
                    st.error(result.get('message', "Failed to check appointments"))
        except requests.exceptions.ConnectionError:
            st.error("Could not connect to the server. Please make sure the server is running.")
        except requests.exceptions.RequestException as e:
            st.error(f"Error checking appointments: {str(e)}")
    
    # Display active appointments if they exist
    if st.session_state.get('appointments'):
        st.markdown("### 📅 Your Active Appointments")
        for appt in st.session_state['appointments']:
            with st.container():
                col1, col2 = st.columns([5, 1])
                with col1:
                    st.markdown(f"""
                    **Date:** {appt['date']}  
                    **Time:** {appt['time']}
                    """)
                with col2:
                    if st.button("Cancel", key=f"cancel_{appt['date']}_{appt['time']}", use_container_width=True):
                        try:
                            with st.spinner("Cancelling your appointment..."):
                                response = requests.post(
                                    f"{API_URL}/cancel_appointment",
                                    json={
                                        "email": appt['email'],
                                        "date": appt['date'],
                                        "time": appt['time']
                                    }
                                )
                                response.raise_for_status()
                                
                                result = response.json()
                                if result.get('success'):
                                    confirmation_msg = f"""✅ **Appointment Cancelled Successfully!**

**Cancelled Appointment Details:**
• Date: {appt['date']}
• Time: {appt['time']}

You will receive a confirmation email shortly.

Need to schedule a new appointment? Just type 'schedule appointment' in the chat."""
                                    st.session_state["messages"].append({"role": "assistant", "content": confirmation_msg})
                                    st.session_state['cancellation_state'] = None
                                    st.session_state['appointments'] = None
                                    st.rerun()
                                else:
                                    st.error(result.get('message', "Failed to cancel appointment"))
                        except requests.exceptions.ConnectionError:
                            st.error("Could not connect to the server. Please make sure the server is running.")
                        except requests.exceptions.RequestException as e:
                            st.error(f"Error cancelling appointment: {str(e)}")
    
    # Display appointment history
    if email:
        display_appointment_history(email)

def handle_appointment_scheduling():
    # Only set state to date_selection if it's not already set
    if st.session_state.get('scheduling_state') is None:
        st.session_state['scheduling_state'] = 'date_selection'
    
    if st.session_state.get('scheduling_state') == 'date_selection':
        st.markdown("### 📅 Schedule Your Appointment")
        st.markdown("Please select your preferred date and time:")
        
        col1, col2 = st.columns([6, 1])
        with col1:
            date = st.date_input("Select Date", min_value=datetime.date.today())
        with col2:
            if st.button("Clear", key="clear_scheduling"):
                # Reset all scheduling-related session state
                st.session_state['scheduling_state'] = 'date_selection'
                st.session_state['selected_date'] = None
                st.session_state['selected_time'] = None
                # Clear the time selection from session state
                if 'time_selection' in st.session_state:
                    del st.session_state['time_selection']
                st.rerun()
                
        if date:
            date_str = date.strftime('%Y-%m-%d')
            try:
                response = requests.post(
                    f"{API_URL}/schedule",
                    json={"action": "check_availability", "date": date_str}
                )
                response.raise_for_status()
                
                available_slots = response.json().get('available_slots', [])
                if available_slots:
                    st.markdown("### ⏰ Available Time Slots")
                    selected_time = st.selectbox(
                        "Select a time slot",
                        options=available_slots,
                        key="time_selection"
                    )
                    
                    if selected_time:
                        if st.button("Continue with selected time", use_container_width=True):
                            st.session_state['selected_date'] = date_str
                            st.session_state['selected_time'] = selected_time
                            st.session_state['scheduling_state'] = 'user_info'
                            st.rerun()
                else:
                    st.warning("No available slots for this date. Please select another date.")
            except requests.exceptions.ConnectionError:
                st.error("Could not connect to the server. Please make sure the server is running.")
            except requests.exceptions.RequestException as e:
                st.error(f"Error checking availability: {str(e)}")
                
    if st.session_state.get('scheduling_state') == 'user_info':
        st.markdown("### 👤 Enter Your Information")
        # Generate a unique form key based on timestamp
        form_key = f"appointment_form_{datetime.datetime.now().timestamp()}"
        
        name = st.text_input("Full Name", placeholder="Enter your full name")
        email = st.text_input("Email", placeholder="Enter your email address")
        phone = st.text_input("Phone", placeholder="Enter your phone number")
        
        st.markdown("### 📅 Selected Appointment")
        st.markdown(f"**Date:** {st.session_state['selected_date']}")
        st.markdown(f"**Time:** {st.session_state['selected_time']}")
        
        col1, col2 = st.columns([6, 1])
        with col1:
            if st.button("Schedule Appointment", type="primary", use_container_width=True):
                if not all([name, email, phone]):
                    st.error("Please fill in all fields.")
                else:
                    try:
                        with st.spinner("Scheduling your appointment..."):
                            response = requests.post(
                                f"{API_URL}/schedule",
                                json={
                                    "action": "book_appointment",
                                    "name": name,
                                    "email": email,
                                    "phone": phone,
                                    "date": st.session_state['selected_date'],
                                    "time": st.session_state['selected_time']
                                }
                            )
                            response.raise_for_status()
                            
                            result = response.json()
                            if result.get('success'):
                                st.success("✅ Appointment scheduled successfully!")
                                confirmation_msg = f"""### 🎉 Appointment Scheduled Successfully!

#### 📋 Appointment Details
---
**👤 Personal Information**
• **Name:** {name}
• **Email:** {email}
• **Phone:** {phone}

**📅 Schedule**
• **Date:** {st.session_state['selected_date']}
• **Time:** {st.session_state['selected_time']}

---
📧 A confirmation email has been sent to your email address.
⏰ Please arrive 5-10 minutes before your scheduled time.
❓ If you need to make any changes, please contact us at +1 (718)-971-9914.

We look forward to seeing you! 😊"""
                                st.markdown(confirmation_msg)
                                
                                # Add to chat history with the same formatting
                                st.session_state["messages"].append({"role": "assistant", "content": confirmation_msg})
                                
                                # Reset scheduling state
                                st.session_state['scheduling_state'] = None
                                st.session_state['selected_date'] = None
                                st.session_state['selected_time'] = None
                                st.rerun()
                            else:
                                st.error(f"Failed to schedule appointment: {result.get('message', 'Unknown error')}")
                    except requests.exceptions.ConnectionError:
                        st.error("Could not connect to the server. Please make sure the server is running.")
                    except requests.exceptions.RequestException as e:
                        st.error(f"Error scheduling appointment: {str(e)}")
        
        with col2:
            if st.button("Cancel", use_container_width=True):
                st.session_state['scheduling_state'] = None
                st.session_state['selected_date'] = None
                st.session_state['selected_time'] = None
                st.rerun()

# Add custom CSS for better UI
st.markdown("""
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
""", unsafe_allow_html=True)

# Initialize session state for chat history
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# Initialize scheduling state
if "scheduling_state" not in st.session_state:
    st.session_state["scheduling_state"] = None

# Initialize cancellation state
if "cancellation_state" not in st.session_state:
    st.session_state["cancellation_state"] = None

# Initialize loading state
if "thinking" not in st.session_state:
    st.session_state["thinking"] = False

# Initialize welcome message
if "initialized" not in st.session_state:
    welcome_message = """👋 **Welcome to New Turbo Education!**

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
    
    st.session_state["messages"] = [
        {"role": "assistant", "content": welcome_message}
    ]
    st.session_state["initialized"] = True

# Streamlit App - Chat UI
st.title("🤖 New Turbo Education AI Assistant")

# Create a container for messages with auto-scroll
chat_container = st.container()

# Process any pending message first (before displaying)
if st.session_state["thinking"]:
    try:
        last_message = st.session_state["messages"][-1]["content"]
        if "cancel" in last_message.lower() and "appointment" in last_message.lower():
            st.session_state['cancellation_state'] = True
            chatbot_reply = """I'll help you cancel your appointment. Here's what you need to do:

1️⃣ Enter your email address in the form below
2️⃣ Click "Check Appointments" to view your active appointments
3️⃣ Click the "Cancel" button next to the appointment you want to cancel

Please proceed with the form below:"""
        else:
            response = requests.post(
                f"{API_URL}/query",
                json={
                    "query": last_message,
                    "conversation_history": st.session_state["messages"][-5:] if len(st.session_state["messages"]) > 1 else []
                }
            )
            response.raise_for_status()
            response_data = response.json()
            chatbot_reply = response_data.get("answer", "I apologize, but I didn't understand that. Could you please rephrase your question?")
            
            if response_data.get("intent") == "schedule_appointment":
                st.session_state['scheduling_state'] = 'date_selection'
                chatbot_reply += "\n\nI'll help you schedule an appointment. Please use the form below:"
    except requests.exceptions.ConnectionError:
        chatbot_reply = "⚠️ **Connection Error**\n\nI couldn't connect to the server. Please make sure the server is running and try again."
    except requests.exceptions.RequestException as e:
        chatbot_reply = f"⚠️ **Error**\n\nI encountered an error: {str(e)}\n\nPlease try again."

    # Add assistant's response to chat history
    st.session_state["messages"].append({"role": "assistant", "content": chatbot_reply})
    st.session_state["thinking"] = False
    st.rerun()

# Display chat history and forms
with chat_container:
    for msg in st.session_state["messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            # Display forms after their respective trigger messages
            if msg == st.session_state["messages"][-1]:  # Only for the last message
                if st.session_state.get('scheduling_state'):
                    handle_appointment_scheduling()
                if st.session_state.get('cancellation_state'):
                    handle_appointment_cancellation()
    
    # Show loading message if thinking
    if st.session_state["thinking"]:
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                st.empty()

# User input field with placeholder
if user_input := st.chat_input("Type your message here...", key="user_input"):
    # Add user message to chat history immediately
    st.session_state["messages"].append({"role": "user", "content": user_input})
    st.session_state["thinking"] = True
    st.rerun()

# Add JavaScript for auto-scrolling
st.markdown("""
<script>
    const messageDiv = document.querySelector('#message-container');
    if (messageDiv) {
        messageDiv.scrollTop = messageDiv.scrollHeight;
    }
</script>
""", unsafe_allow_html=True)
