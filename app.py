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
from appointments import get_available_slots, save_appointment, send_confirmation_email

import pandas as pd
import datetime



_ = load_dotenv(find_dotenv())
openai_api_key = os.getenv("OPENAI_API_KEY")
# openai_base_url = os.getenv("OPENAI_BASE_URL")

if not openai_api_key:
    raise ValueError("OpenAI API key is missing. Please set it in .env")

# Initialize OpenAI client
client = OpenAI()


# Load the prompt from the root folder
# base_dir = os.path.dirname(os.path.abspath(__file__))  # This points to chatbot/
# root_dir = os.path.abspath(os.path.join(base_dir, ".."))  # Go up one level

# Construct the full path to the prompt file


try:
    with open("prompt.md", "r", encoding="utf-8") as f:
        system_prompt = f.read().strip()
except FileNotFoundError:
    system_prompt = "You are a helpful AI assistant."  # Default fallback prompt



# Set up LlamaIndex
llm = LlamaOpenAI(model="gpt-4o-mini", api_key=openai_api_key)

Settings.llm = llm
Settings.chunk_size = 512
Settings.chunk_overlap = 20


# Load and index documents
def initialize_index():
    # Load documents from the data directory
    documents = SimpleDirectoryReader('data').load_data()
    
    # Create text splitter
    text_splitter = TokenTextSplitter(chunk_size=300, chunk_overlap=100)
    
    # Create index
    index = VectorStoreIndex.from_documents(documents)
    return index

# Initialize the index
index = initialize_index()

# Set up retrievers
vector_retriever = index.as_retriever()

# Combine retrievers
retriever_dict = {
    "bm25": vector_retriever,
    "vector": vector_retriever
}
hybrid_retriever = RecursiveRetriever(retriever_dict=retriever_dict, root_id="bm25")



# # Apply Reranking for better result
reranker = SentenceTransformerRerank(model="BAAI/bge-reranker-large", top_n=5)
query_engine = RetrieverQueryEngine(retriever=hybrid_retriever, node_postprocessors=[reranker])


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



def get_completion(user_input, response_format="text", model="gpt-4o-mini"):
    # Get relevant context from the index
    response = query_engine.query(user_input)
    
    print("🔍 Query Sent to OpenAI:", user_input)
    print("📝 Context Retrieved:", response)
    
    # Add price information for price-related queries
    price_related_keywords = ['price', 'cost', 'fee', 'expensive', 'cheap', 'dollar', 'payment', 'pricing']
    if any(keyword in user_input.lower() for keyword in price_related_keywords):
        price_info = load_price_data()
        context = f"{response.response}\n\nAdditional pricing information:\n{price_info}"
    else:
        context = response.response
    
    # Construct prompt with retrieved context
    augmented_prompt = f"""Based on the following context, please answer the question. 
    If the answer cannot be found in the context, say 'I am not sure, but you can contact our support at 718-971-9914 or newturbony@gmail.com.'
    
    Context: {response.response}
    
    
    
    Question: {user_input}
    
    """
    
    print("📢 Final Prompt to OpenAI:", augmented_prompt)
    
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



app = Flask(__name__)
CORS(app)

@app.route('/query', methods=['POST'])
def answer_query():
    try:
        data = request.json
        if not data or 'query' not in data:
            return jsonify({"error": "No query provided"}), 400
        
        user_query = data.get("query").lower().strip()
        answer = get_completion(user_query)
        return jsonify({"answer": answer})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/schedule', methods=['POST'])
def handle_scheduling():
    try:
        data = request.json
        action = data.get('action')
        
        if action == 'check_availability':
            date = data.get('date')
            available_slots = get_available_slots(date)
            return jsonify({
                "available_slots": available_slots
            })
            
        elif action == 'book_appointment':
            appointment_data = {
                'name': data.get('name'),
                'email': data.get('email'),
                'phone': data.get('phone'),
                'date': data.get('date'),
                'time': data.get('time'),
                'created_at': datetime.datetime.now().isoformat()
            }
            
            save_appointment(appointment_data)
            send_confirmation_email(appointment_data)
            
            return jsonify({
                "success": True,
                "message": "Appointment scheduled successfully"
            })
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
   