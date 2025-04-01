# 🧠 AI Assistant for New Turbo Education

An AI-powered chatbot for **New Turbo Education** designed to assist with customer inquiries, pricing information, course details, and appointment scheduling. This assistant leverages **GPT-4**, **LlamaIndex**, and **Flask**, with optional **Streamlit** frontend integration for a web-based interface.

---
## ⚙️ How It Works
- The backend uses retrieval-augmented generation (RAG) to answer user questions based on:
    * Markdown files with institutional details (teacher bios, rules, course types)
    * CSV files with up-to-date pricing
    * A custom system prompt that controls the assistant’s tone and behavior

- When a user submits a query:
    * The question is searched against vectorized documents (/data/*.md) using LlamaIndex.
    * The assistant optionally adds price info if pricing keywords are detected.
    * A combined prompt is sent to OpenAI GPT-4o-mini for response generation.
    * A formatted answer is returned to the user.

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
EMAIL_ADDRESS=sender_email_address
EMAIL_PASSWORD=sender_email_app_password
ADMIN_EMAIL=admin_email_address
API_URL=your_api_url
```

### Create a database for storing appointment information
```bash
run db_utils.py 
```


### 5. Run the App locally
```bash
python app.py  # backend
streamlit run UI/ui.py # frontend
```


---
## 📌 Appointment Scheduling Use Case 
**1. Initial Interaction**
User: "I would like to schedule an SAT course"

AI助手: "I'll help you with your appointment. Please provide your information and select what you'd like to do below:

我将帮您处理预约事宜。请在下方提供您的信息并选择您想进行的操作："

**2. Information Collection and Service Selection Interface**

System displays a form:

- Full Name | 姓名: [input]
- Email Address | 邮箱: [input]
- Phone Number | 电话: [input]

Service Selection Options | 服务选择选项:

* Schedule a new appointment | 预约新课程
* Cancel an existing appointment | 取消现有预约
* Check appointment status | 查询预约状态

[Continue | 继续] 


**3. Date Selection Interface**

System displays:

"📅 Select Appointment Date | 选择预约日期"

[Calendar interface, showing dates for the next 90 days]

[Back | 返回] [Continue | 继续]


**4. Time Selection Interface:**
System displays:

"⏰ Select Appointment Time | 选择预约时间"

可用时间段列表：
[Dropdown menu showing all available time slots for the selected date]

[Back | 返回] [Schedule Appointment | 确认预约] 


**5. Appointment Confirmation**

System displays success message:

"Appointment scheduled successfully! | 预约成功！"

[Back to Main Menu | 返回主菜单] 

