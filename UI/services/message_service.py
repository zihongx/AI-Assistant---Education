import requests
import logging
import os
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
_ = load_dotenv()
API_URL = os.getenv("API_URL", "http://127.0.0.1:5000")

def process_message(message, conversation_history=None):
    """Process user message and detect intent"""
    try:
        logger.info(f"Processing message: {message[:30]}...")
        
        # Send to backend for LLM-based intent detection
        response = requests.post(
            f"{API_URL}/query",
            json={
                "query": message,
                "conversation_history": conversation_history or []
            }
        )
        response.raise_for_status()
        response_data = response.json()
        
        # Get LLM intent detection result
        detected_intent = response_data.get("intent", "")
        
        # Fallback keyword-based detection
        appointment_keywords = [
            "cancel", "cancellation", "取消", "终止", "撤销",
            "schedule", "book", "appointment", "预约", "约", "预定",
            "check", "status", "history", "查询", "状态", "历史"
        ]
        
        # Check if this is any kind of appointment-related request
        is_appointment_intent = (
            detected_intent in ["cancel_appointment", "schedule_appointment", "check_status"] or
            any(k in message.lower() for k in appointment_keywords)
        )
        
        return {
            'success': True,
            'intent': detected_intent,
            'is_appointment_intent': is_appointment_intent,
            'response': response_data.get("answer", "I apologize, but I didn't understand that. Could you please rephrase your question?")
        }
        
    except requests.exceptions.ConnectionError:
        logger.error("Connection error while querying API")
        return {
            'success': False,
            'message': "⚠️ **Connection Error**\n\nI couldn't connect to the server. Please make sure the server is running and try again."
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Error querying API: {str(e)}")
        return {
            'success': False,
            'message': f"⚠️ **Error**\n\nI encountered an error: {str(e)}\n\nPlease try again."
        } 