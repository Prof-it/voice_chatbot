# ENTChat 🩺🤖  
**An AI-powered healthcare chatbot for diagnosing ENT conditions and checking medication side effects**

ENTChat is an open-source AI chatbot designed to help users self-assess Ear, Nose, and Throat (ENT) symptoms using natural language. It predicts possible ENT conditions and fetches related medication and side-effect data using machine learning and FDA datasets.

---

## 🧠 Features

- 🔍 Symptom-based ENT disease prediction using ML
- 💬 Natural language input with OpenAI-powered interpretation
- 💊 Medication and side-effect lookup via FDA APIs
- ⚙️ FastAPI backend + React frontend
- 🔁 Dockerized for local development and deployment

---

## 🚀 Quickstart (with Docker)

Make sure OPENAI_API_KEY and DEBUG is set in backend/.env
Make sure BACKEND_URL=http://localhost:8000 is set in frontend/.env

> 🐳 Make sure Docker + Docker Compose is installed.

```bash
# Clone the repo
git clone https://github.com/krishsat9937/ent_chatbot.git
cd ENTChat

# Run everything
docker-compose up --build
```
---

🧪 Local Development

Backend (FastAPI)

```
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Frontend (React)

```
cd frontend
npm install
npm start
```

