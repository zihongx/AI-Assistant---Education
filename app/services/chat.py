from openai import OpenAI
import logging
import os
import json
from app.config.settings import MODEL_CONFIG, SYSTEM_PROMPT, PRICES_CSV_PATH
from app.services.vector_store import VectorStoreService
from app.services.intent_detection import IntentDetectionService
import pandas as pd

# Set up logging
logger = logging.getLogger(__name__)

class ChatService:
    def __init__(self):
        self.client = OpenAI()
        self.model = MODEL_CONFIG['MODEL_NAME']
        self.vector_store = VectorStoreService()
        self.intent_detector = IntentDetectionService()
        self.prices_path = PRICES_CSV_PATH
        self.confidence_threshold_high = 0.7
        self.confidence_threshold_medium = 0.4
        logger.info("Chat service initialized")

    def load_price_data(self) -> str:
        """Load and format price data from CSV"""
        try:
            logger.info(f"Loading price data from: {self.prices_path}")
            df = pd.read_csv(self.prices_path)
            price_info = "Here are our course prices:\n\n"
            for _, row in df.iterrows():
                price_info += (f"{row['Course Name']} - {row['Course Level']}\n"
                             f"Duration: {row['Hours']} hours\n"
                             f"Price: ${row['Price (USD)']}\n\n")
            logger.info(f"Successfully loaded {len(df)} price entries")
            return price_info
        except Exception as e:
            logger.error(f"Error loading price data: {str(e)}")
            return ""
            
    def verify_intent_with_llm(self, user_query: str, initial_intent: dict, conversation_history: list = None) -> dict:
        """
        Use the main LLM to verify and potentially correct the intent when confidence is medium
        
        Args:
            user_query: The user's input
            initial_intent: The intent detected by the intent detection service
            conversation_history: Optional list of previous messages
            
        Returns:
            Updated intent dictionary with potentially improved classification
        """
        try:
            # Only use this for medium confidence results
            confidence = initial_intent.get("confidence", 0)
            if confidence >= self.confidence_threshold_high or confidence < self.confidence_threshold_medium:
                return initial_intent
                
            logger.info(f"Verifying medium-confidence intent with LLM: {initial_intent.get('intent')} ({confidence:.2f})")
            
            # Format conversation history
            history_context = ""
            if conversation_history and len(conversation_history) > 0:
                history_context = "Previous conversation:\n"
                for i, msg in enumerate(conversation_history[-3:]):  # Include up to 3 most recent messages
                    role = "User" if msg["role"] == "user" else "Assistant"
                    history_context += f"{role}: {msg['content']}\n"
                    
            # Create a prompt for the LLM to verify the intent
            messages = [
                {"role": "system", "content": """You are an intent verification system. 
                Your job is to analyze the user's query in context and determine if the initial intent classification is correct.
                
                Available intents are:
                - "schedule_appointment": User wants to book, schedule, or make an appointment
                - "price_query": User is asking about costs, fees, pricing
                - "general_query": Any other information request
                
                Consider the conversation history and the exact wording of the query. Be more sensitive to appointment-related and price-related queries as these have special handling.
                """},
                {"role": "user", "content": f"""
                Initial intent classification: {initial_intent.get('intent')}
                Initial confidence: {confidence}
                
                {history_context}
                
                User query: {user_query}
                
                Based on this information, what is the most appropriate intent classification?
                Respond with a JSON object containing:
                - "intent": one of ["schedule_appointment", "price_query", "general_query"]
                - "confidence": a number between 0 and 1
                - "explanation": a brief explanation of why you classified it this way
                """}
            ]
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            # Parse the JSON response
            try:
                llm_intent = json.loads(response.choices[0].message.content)
                logger.info(f"LLM verified intent: {llm_intent.get('intent')} with confidence {llm_intent.get('confidence')}")
                return llm_intent
            except json.JSONDecodeError:
                logger.error("Failed to parse LLM intent verification response")
                return initial_intent
                
        except Exception as e:
            logger.error(f"Error in intent verification: {str(e)}")
            return initial_intent  # Fall back to the original intent

    def get_hybrid_intent(self, user_query: str, conversation_history: list = None) -> dict:
        """
        Get intent using a hybrid approach combining dedicated intent detection and LLM verification
        
        Args:
            user_query: The user's input
            conversation_history: Optional list of previous messages
            
        Returns:
            Intent dictionary with the most accurate classification
        """
        # First use the dedicated intent detection service
        initial_intent = self.intent_detector.detect_intent(user_query)
        confidence = initial_intent.get("confidence", 0)
        
        logger.info(f"Initial intent detection: {initial_intent.get('intent')} with confidence {confidence}")
        
        # For high confidence results, use as is
        if confidence >= self.confidence_threshold_high:
            return initial_intent
            
        # For medium confidence, verify with LLM
        if confidence >= self.confidence_threshold_medium:
            return self.verify_intent_with_llm(user_query, initial_intent, conversation_history)
            
        # For low confidence, it's already a general query
        return initial_intent

    def get_completion(self, user_input: str, conversation_history: list = None) -> str:
        """Get a completion for the user's input"""
        try:
            # Get intent using hybrid approach
            intent_data = self.get_hybrid_intent(user_input, conversation_history)
            logger.info(f"Final intent: {intent_data.get('intent')} with confidence: {intent_data.get('confidence', 0)}")
            
            # Get context from vector store
            context = self.vector_store.query(user_input, conversation_history)
            
            # Add price information for price-related queries
            if intent_data.get("intent") == "price_query" and intent_data.get("confidence", 0) > self.confidence_threshold_medium:
                logger.info("Appending price information to context")
                price_info = self.load_price_data()
                context = f"{context}\n\nAdditional pricing information:\n{price_info}"
            
            # Get completion from OpenAI
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": context}
            ]
            
            logger.info(f"Sending request to OpenAI with model: {self.model}")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error in get_completion: {str(e)}")
            return "I apologize, but I encountered an error processing your request. Please try again." 