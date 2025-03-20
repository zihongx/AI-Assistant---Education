import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv, find_dotenv
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.core import Settings
from llama_index.core.postprocessor import SentenceTransformerRerank
from llama_index.core.retrievers import RecursiveRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.llms.openai import OpenAI as LlamaOpenAI
from llama_index.core.text_splitter import TokenTextSplitter
from appointments import appointment_manager  
import json
import sqlite3

import pandas as pd
import datetime
import requests


CONFIG = {
    'MODEL_NAME': 'gpt-4o-mini',  # or 'gpt-3.5-turbo'
    'CONFIDENCE_THRESHOLD': 0.7,
    'TEMPERATURE': 0.7,
    'MAX_TOKENS': 1000
}

_ = load_dotenv(find_dotenv())
openai_api_key = os.getenv("OPENAI_API_KEY")
# openai_base_url = os.getenv("OPENAI_BASE_URL")

if not openai_api_key:
    raise ValueError("OpenAI API key is missing. Please set it in .env")


# Initialize OpenAI client
client = OpenAI()


# Construct the full path to the prompt file
try:
    with open("prompt.md", "r", encoding="utf-8") as f:
        system_prompt = f.read().strip()
except FileNotFoundError:
    system_prompt = """I am an AI assistant for New Turbo Education, a tutoring center specializing in SAT, AP, ACT, SHSAT, TOEFL, ESL, and college admissions consulting. I provide bilingual responses in English and Chinese to help both parents and students. I aim to be professional, friendly and helpful in answering questions about courses, tutoring, pricing, schedules and other education-related topics."""  # Default fallback prompt



# Set up LlamaIndex
llm = LlamaOpenAI(model="gpt-4o-mini", api_key=openai_api_key)

# Consistent chunk settings
CHUNK_SIZE = 512
CHUNK_OVERLAP = 100

Settings.llm = llm
Settings.chunk_size = CHUNK_SIZE
Settings.chunk_overlap = CHUNK_OVERLAP

# Load and index documents
def initialize_index():
    try:
        # Load documents from the data directory
        documents = SimpleDirectoryReader('data').load_data()
        
        # Create text splitter with consistent settings
        text_splitter = TokenTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP
        )
        
        # Create index with text splitter
        index = VectorStoreIndex.from_documents(
            documents,
            text_splitter=text_splitter,
            show_progress=True
        )
        return index
    except Exception as e:
        print(f"Error initializing index: {str(e)}")
        raise

# Initialize the index
index = initialize_index()

# Set up vector retriever
from llama_index.core.retrievers import VectorIndexRetriever

# Create vector retriever
vector_retriever = VectorIndexRetriever(
    index=index,
    similarity_top_k=5
)

# Apply reranking for better results
reranker = SentenceTransformerRerank(
    model="BAAI/bge-reranker-large",
    top_n=3  # Reduced from 5 to focus on most relevant results
)

# Create query engine with reranking
query_engine = RetrieverQueryEngine(
    retriever=vector_retriever,
    node_postprocessors=[reranker]
)


def load_price_data():
    """Load and format price data from CSV"""
    df = pd.read_csv('data/prices.csv')
    # Create a formatted string of all price information
    price_info = "Here are our course prices:\n\n"
    for _, row in df.iterrows():
        price_info += (f"{row['Course Name']} - {row['Course Level']}\n"
                      f"Duration: {row['Hours']} hours\n"
                      f"Price: ${row['Price (USD)']}\n\n")
    return price_info


def detect_intent(user_query):
    """Internal function to detect intent without making HTTP request"""
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
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
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

def get_completion(user_input, response_format="text", model="gpt-4o-mini", conversation_history=None):
    try:
        # Get relevant context from the index
        response = query_engine.query(user_input)
        
        # print("🔍 Query Sent to OpenAI:", user_input)
        # print("📝 Context Retrieved:", response)
        
        # Detect intent directly without HTTP request
        intent_data = detect_intent(user_input)
        
        # Add price information for price-related queries
        if intent_data.get("intent") == "price_query" and intent_data.get("confidence", 0) > 0.7:
            price_info = load_price_data()
            context = f"{response.response}\n\nAdditional pricing information:\n{price_info}"
        else:
            context = response.response

        # Format conversation history if available
        history_context = ""
        if conversation_history:
            history_context = "Previous conversation:\n"
            for msg in conversation_history:
                role = "User" if msg["role"] == "user" else "Assistant"
                history_context += f"{role}: {msg['content']}\n"
            history_context += "\n"
        
        # Construct prompt with retrieved context and conversation history
        augmented_prompt = f"""Based on the following context, conversation history, and your knowledge as an AI assistant, please answer the question.
        If the answer cannot be found in the context, say 'I am not sure, but you can contact our support at 718-971-9914 or newturbony@gmail.com.'
        
        {history_context}
        Context: {context}
        
        Question: {user_input}
        """
        
        # print("📢 Final Prompt to OpenAI:", augmented_prompt)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": augmented_prompt}
        ]        
        
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
            response_format={"type": response_format},
        )
        
        print("🔍 Full API Response:", response) 
        
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error in get_completion: {str(e)}")
        return "I apologize, but I encountered an error processing your request. Please try again."


app = Flask(__name__)
CORS(app)

@app.route('/detect_intent', methods=['POST'])
def detect_intent_route():
    try:
        data = request.json
        if not data or 'query' not in data:
            return jsonify({"error": "No query provided"}), 400
        
        user_query = data.get("query")
        
        # Use OpenAI to detect intent
        intent_data = detect_intent(user_query)
        return jsonify({"intent_data": intent_data})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/query', methods=['POST'])
def answer_query():
    try:
        data = request.json
        if not data or 'query' not in data:
            return jsonify({"error": "No query provided"}), 400
        
        user_query = data.get("query").lower().strip()
        conversation_history = data.get("conversation_history", [])
        
        # Detect intent directly
        intent_data = detect_intent(user_query)
        
        # If it's an appointment intent, return special response
        if intent_data.get("intent") == "schedule_appointment" and intent_data.get("confidence", 0) > 0.7:
            return jsonify({
                "answer": "I understand you'd like to schedule an appointment. Let me help you with that.",
                "intent": "schedule_appointment"
            })
        
        # Otherwise proceed with regular query
        answer = get_completion(user_query, conversation_history=conversation_history)
        return jsonify({
            "answer": answer, 
            "intent": intent_data.get("intent", "general_query")
        })
    except Exception as e:
        print(f"Error in answer_query: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/schedule', methods=['POST'])
def handle_scheduling():
    try:
        data = request.json
        print(f"Received scheduling request: {data}")  # Debug log
        action = data.get('action')
        
        if action == 'check_availability':
            date = data.get('date')
            print(f"Checking availability for date: {date}")  # Debug log
            available_slots = appointment_manager.get_available_slots(date)
            print(f"Available slots: {available_slots}")  # Debug log
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
            print(f"Attempting to save appointment: {appointment_data}")  # Debug log
            
            try:
                # Validate the data before saving
                if not all([appointment_data['name'], appointment_data['email'], 
                          appointment_data['phone'], appointment_data['date'], 
                          appointment_data['time']]):
                    raise ValueError("Missing required fields")
                
                # Check if the date is valid
                try:
                    datetime.datetime.strptime(appointment_data['date'], '%Y-%m-%d')
                except ValueError:
                    raise ValueError("Invalid date format")
                
                # Check if the time is valid
                try:
                    datetime.datetime.strptime(appointment_data['time'], '%H:%M')
                except ValueError:
                    raise ValueError("Invalid time format")
                
                # Initialize database if it doesn't exist
                if not os.path.exists('data/appointments.db'):
                    print("Database not found, initializing...")
                    os.makedirs('data', exist_ok=True)
                    with sqlite3.connect('data/appointments.db') as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            CREATE TABLE IF NOT EXISTS users (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                name TEXT NOT NULL,
                                email TEXT UNIQUE NOT NULL,
                                phone TEXT NOT NULL
                            )
                        """)
                        cursor.execute("""
                            CREATE TABLE IF NOT EXISTS appointments (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                user_id INTEGER NOT NULL,
                                appointment_time DATETIME NOT NULL UNIQUE,
                                status TEXT CHECK(status IN ('scheduled', 'canceled')) DEFAULT 'scheduled',
                                FOREIGN KEY (user_id) REFERENCES users (id)
                            )
                        """)
                        conn.commit()
                
                appointment_manager.save_appointment(appointment_data)
                print("Appointment saved successfully")  # Debug log
                return jsonify({
                    "success": True,
                    "message": "Appointment scheduled successfully"
                })
            except Exception as e:
                print(f"Error saving appointment: {str(e)}")  # Debug log
                return jsonify({
                    "success": False,
                    "message": str(e)
                }), 400
            
    except Exception as e:
        print(f"Unexpected error: {str(e)}")  # Debug log
        return jsonify({"error": str(e)}), 500

@app.route('/cancel_appointment', methods=['POST'])
def handle_cancellation():
    try:
        data = request.json
        if not data or 'email' not in data or 'date' not in data or 'time' not in data:
            return jsonify({"error": "Missing required fields"}), 400
        
        result = appointment_manager.cancel_appointment(data)
        
        if result.get('success'):
            return jsonify({
                "success": True,
                "message": "Appointment cancelled successfully"
            })
        else:
            return jsonify({
                "success": False,
                "message": result.get('message', "Appointment not found")
            }), 404
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/check_appointments', methods=['POST'])
def check_appointments():
    try:
        data = request.json
        if not data or 'email' not in data:
            return jsonify({"error": "Email is required"}), 400
            
        with appointment_manager.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    u.name,
                    u.email,
                    u.phone,
                    date(a.appointment_time) as date,
                    strftime('%H:%M', a.appointment_time) as time,
                    a.status
                FROM appointments a
                JOIN users u ON a.user_id = u.id
                WHERE u.email = ?
                AND a.status = 'scheduled'
                ORDER BY a.appointment_time
            """, (data['email'],))
            
            appointments = []
            for row in cursor.fetchall():
                appointments.append({
                    'name': row[0],
                    'email': row[1],
                    'phone': row[2],
                    'date': row[3],
                    'time': row[4],
                    'status': row[5]
                })
                
            return jsonify({
                "success": True,
                "appointments": appointments
            })
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/appointment_history', methods=['POST'])
def get_appointment_history():
    try:
        data = request.json
        if not data or 'email' not in data:
            return jsonify({"error": "Email is required"}), 400
            
        appointments = appointment_manager.get_appointment_history(data['email'])
        return jsonify({
            "success": True,
            "appointments": appointments
        })
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
   