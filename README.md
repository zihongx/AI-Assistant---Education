# 🧠 AI Assistant for New Turbo Education

An AI-powered chatbot for **New Turbo Education** designed to assist with customer inquiries, pricing information, course details, and appointment scheduling. This assistant leverages **GPT-4**, **LlamaIndex**, and **Flask**, with optional **Streamlit** frontend integration for a web-based interface.

---

## 🚀 Features

- 🤖 Converses naturally with users using OpenAI GPT-4
- 📚 Pulls answers from uploaded documents using LlamaIndex
- 💵 Automatically responds with course pricing from a CSV file
- 📆 Supports appointment-related queries
- 🌐 CORS-enabled Flask backend, ready for frontend integration

---

## 🏗️ Tech Stack

- Python 3.10+
- Flask (RESTful API backend)
- OpenAI (GPT-4 via API)
- LlamaIndex (document indexing + retrieval)
- Pandas (price data processing)
- Streamlit (frontend)


---

## 🧰 Installation

### 1. Clone the Repo
```bash
git clone https://github.com/zihongx/AI-Assistant---Education.git
cd AI-Assistant---Education
```
### 2. Create Virtual Environment (Optional)
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```
### 3. Install Dependencies
```bash
pip install -r requirements.txt
```
### 4. Create a .env file in the root directory with the following content:
```bash
OPENAI_API_KEY=your_openai_api_key
EMAIL_ADDRESS=your_email_address
EMAIL_PASSWORD=your_email_app_password
API_URL=your_api_url
```
### 5. Run the App locally
```bash
python app.py
streamlit run ui.py # run streamlit on a new terminal
```
