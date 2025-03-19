import streamlit as st
import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv('API_URL', 'http://127.0.0.1:5000')

# Streamlit App - Chat UI
st.title("🤖 New Turbo Education AI Assistant")

# Initialize session state for chat history
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# Initialize scheduling state
if "scheduling_state" not in st.session_state:
    st.session_state["scheduling_state"] = None

# Display chat history
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# User input field
if user_input := st.chat_input("Type your message..."):
    # Append user message to chat history
    st.session_state["messages"].append({"role": "user", "content": user_input})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(user_input)

    # Regular chat flow with intent detection
    try:
        response = requests.post(
            f"{API_URL}/query",
            json={"query": user_input}
        )
        response.raise_for_status()
        response_data = response.json()
        chatbot_reply = response_data.get("answer", "Sorry, I didn't understand that.")
        
        # Check if the response indicates appointment intent
        if response_data.get("intent") == "schedule_appointment":
            st.session_state['scheduling_state'] = 'date_selection'
    except requests.exceptions.RequestException as e:
        chatbot_reply = f"Error communicating with the server: {str(e)}"

    # Append bot response to chat history
    st.session_state["messages"].append({"role": "assistant", "content": chatbot_reply})

    # Display bot response
    with st.chat_message("assistant"):
        st.markdown(chatbot_reply)

# Add to your existing UI code
def handle_appointment_scheduling():
    st.session_state['scheduling_state'] = 'date_selection'
    
    if st.session_state.get('scheduling_state') == 'date_selection':
        date = st.date_input("Select a date")
        if date:
            date_str = date.strftime('%Y-%m-%d')
            response = requests.post(
                f"{API_URL}/schedule",
                json={"action": "check_availability", "date": date_str}
            )
            
            available_slots = response.json().get('available_slots', [])
            if available_slots:
                selected_time = st.selectbox("Choose a time:", available_slots)
                if selected_time:
                    st.session_state['selected_date'] = date_str
                    st.session_state['selected_time'] = selected_time
                    st.session_state['scheduling_state'] = 'user_info'
            else:
                st.error("No available slots for this date")
                
    if st.session_state.get('scheduling_state') == 'user_info':
        with st.form("appointment_form"):
            name = st.text_input("Name")
            email = st.text_input("Email")
            phone = st.text_input("Phone")
            
            if st.form_submit_button("Schedule Appointment"):
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
                
                if response.json().get('success'):
                    st.success("Appointment scheduled successfully!")
                    st.session_state['scheduling_state'] = None
                else:
                    st.error("Failed to schedule appointment")

# Add this to your chat input handling
if st.session_state.get('scheduling_state'):
    handle_appointment_scheduling()
