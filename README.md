# SymptomSage 🩺🤖  
*An Edge-AI Chatbot for Symptom Extraction and Appointment Pre-Fill*  
*A Master's Thesis Project – “From Voice to Booking: An Edge-AI Pipeline for Symptom Extraction and Appointment Pre-Fill in Clinical Settings”*

**SymptomSage** is an open-source healthcare chatbot developed as part of a Master's thesis project. It helps users describe symptoms naturally, predicts conditions using machine learning, and shares structured appointment data. This prototype serves as a core module in a broader Edge-AI pipeline aimed at automating clinical intake workflows.

---

## 🧠 Key Features

- 🔍 **Symptom-Based Condition Prediction** – Machine learning-based diagnosis using natural language input  
- 💬 **Conversational Interface** – Interprets user input via OpenAI’s GPT API  
- 📦 **Modular Design** – Can be extended to cover other medical domains and scheduling use cases  
- ⚙️ **Modern Stack** – FastAPI backend, React frontend, containerized with Docker  
- 🧩 **Edge-AI Ready** – Designed with edge deployment scenarios in mind  

---

## 🎓 Project Context

This project is part of the MSc Computer Science thesis at IU International University of Applied Sciences, supervised by **Prof. Dr. Tianxiang Lu**. It contributes to research on **Edge-AI in Healthcare**, especially in improving early diagnosis and automating appointment pre-fill workflows in clinical environments.

---

## 🚀 Getting Started (with Docker)

### Prerequisites:
- Docker & Docker Compose installed  
- Environment variables configured:

  - `backend/.env`:  
    ```
    OPENAI_API_KEY=your_openai_key  
    DEBUG=True  
    ```

  - `frontend/.env`:  
    ```
    BACKEND_URL=http://localhost:8000  
    ```

### Run the Project:
```bash
# Clone the repository
git clone https://github.com/krishsat9937/voice_chatbot.git
cd voice_chatbot

# Build and launch containers
docker-compose up --build
```

---

## 🧪 Local Development Setup

### Backend (FastAPI)
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend (React)
```bash
cd frontend
npm install
npm start
```

---

## 🖥️ System Architecture  
*TBD – Will include integration flow from voice transcription to symptom interpretation and API interactions*

---

## 🧊 Edge Deployment  
*TBD – Will detail Raspberry Pi deployment for clinical use cases*

---

## 📄 License  
MIT License – see [`LICENSE`](LICENSE) for details.

---
