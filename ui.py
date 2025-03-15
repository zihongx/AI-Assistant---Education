import streamlit as st
import requests

# Streamlit App - Chat UI
st.title("🤖 AI Chatbot")

# Initialize session state for chat history
if "messages" not in st.session_state:
    st.session_state["messages"] = []

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

    # Send the user query to the backend (your Flask API)
    response = requests.post(
        "http://127.0.0.1:5000/query",
        json={"query": user_input}
    )

    # Extract the chatbot's response
    chatbot_reply = response.json().get("answer", "Sorry, I didn't understand that.")

    # Append bot response to chat history
    st.session_state["messages"].append({"role": "assistant", "content": chatbot_reply})

    # Display bot response
    with st.chat_message("assistant"):
        st.markdown(chatbot_reply)
