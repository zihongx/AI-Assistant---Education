from openai import OpenAI
from app.config.settings import MODEL_CONFIG
import json

class IntentDetectionService:
    def __init__(self):
        self.client = OpenAI()
        self.model = MODEL_CONFIG['MODEL_NAME']

    def detect_intent(self, user_query: str) -> dict:
        """Detect the intent of the user's query"""
        try:
            messages = [
                {"role": "system", "content": """You are an intent detection system. Analyze the user's message and determine their intent.
                Respond with a JSON object containing:
                - "intent": one of ["schedule_appointment", "price_query", "general_query"]
                - "confidence": a number between 0 and 1
                - "explanation": a brief explanation of why you classified it this way
                
                Consider these variations:
                
                For appointment scheduling:
                - "I want to book a class"
                - "Can I schedule a lesson?"
                - "I need to make an appointment"
                - "When can I come in?"
                - "I'd like to sign up for a session"
                
                For price queries:
                - "How much does it cost?"
                - "What are your fees?"
                - "Is it expensive?"
                - "What's the price?"
                - "How much do you charge?"
                - "What are the rates?"
                - "Is there a discount?"
                - "Do you have any special offers?"
                """},
                {"role": "user", "content": user_query}
            ]
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            # Parse the JSON response
            intent_data = json.loads(response.choices[0].message.content)
            return intent_data
        except Exception as e:
            print(f"Error in detect_intent: {str(e)}")
            return {"intent": "general_query", "confidence": 0.0, "explanation": "Error in intent detection"} 