# TCM Clinic Chatbot 💬

## 📖 Overview

ClinicBot is an AI-powered chatbot designed to help patients quickly find the information they need from a clinic’s website—without endless clicking and searching.  
With natural language queries, ClinicBot answers questions about services, pricing, and clinic info, and can even guide users to the right practitioner’s booking page.  

## ✨ Features

- **Instant Answers** – Users can ask about services, pricing, and clinic information.  
- **Booking Guidance** – The bot links directly to relevant practitioner booking pages.  
- **Language Auto-Detection** – Chatbot automatically detects and responds in the user’s language.  
- **PII Protection** – Sensitive user data is automatically detected and redacted before processing or storage.  
- **Contextual Memory** – Conversations maintain context within the session for smoother interactions.  
- **Modern UI** – Built with Streamlit for a clean and simple interface.  

## 🛠️ Tech Stack

- **Frontend:** [Streamlit](https://streamlit.io/)  
- **Backend:** [FastAPI](https://fastapi.tiangolo.com/)  
- **AI / Orchestration:** [LangChain](https://www.langchain.com/) + [OpenAI](https://openai.com/)
- **Database:** local: [SQLite](https://sqlite.org/) | production: PostgreSQL
- **Vector Store:** [Chroma](https://www.trychroma.com/)  
- **Deployment:** [Docker](https://www.docker.com/) + [GCP](https://cloud.google.com/)

## 🚀 Quick Start

### Prerequisites

*   Python 3.9+  
*   Docker Desktop
*   OpenAI API Key

### Installation and Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/ariellinfy/clinicbot.git
   cd clinicbot
   ```

2. **Set up `.env` file in root folder (optional)**
   ```env
   DATA_DIR=/app/data/json
   SQL_DB_URL=your_postgres_db_url
   CHROMA_HOST=chroma

   LLM_MODEL=gpt-4.1-nano-2025-04-14
   OPENAI_EMBED_MODEL=text-embedding-3-small

   ALLOW_ORIGINS="*"
   JANEAPP_BASE=https://demo.janeapp.com
   DEBUG=true

   API_BASE=http://api:8080
   ```
   If not provided, SQL DB will default to local SQLite, and all other variables will fall back to the above defaults.


3. **Build and Run with Docker Compose**
   ```bash
   docker-compose up --build -d
   ```
   This will build the Docker images for the frontend, backend, and Chroma, and start all services in background.

The application will be available at:

- Frontend: `http://localhost:8501`
- Backend API: `http://localhost:8080`
- Chroma: `http://localhost:8000`

## 📚 API Documentation

### Endpoints

- `GET /health` - Health check
- `POST /chat` - Chat with the AI assistant
- `POST /ingest` - Ingest new data
- `POST /reset-session` - Reset chat session
- `POST /set-api-key` - Set OpenAI API key

### Example
```bash
curl http://localhost:8080/health
```

## 📊 Data Management

### Data Ingestion

The system supports JSON data files for:

- Clinic information `clinic.json`
- Team members and practitioners `team_members.json`
- Services offered `services.json`
- Pricing information `pricing.json`
- Frequently asked questions `faqs.json`

Place JSON files in the `data/json/` directory and use the `/ingest` endpoint.

### Database Schema

The SQL database includes tables for:

- `clinic_info` - Basic clinic information
- `team_members` - Staff and practitioner details
- `services` - Available services
- `pricing` - Service pricing
- `faqs` - Frequently asked questions

## 📂 Project Structure

```
clinicbot/
├── backend/                  # FastAPI backend application
│   ├── app/                  # Main application logic
│   │   ├── api.py            # FastAPI routes and endpoints
│   │   ├── models/           # Data models
│   │   ├── services/         # Business logic and services (e.g., ingestion, pipeline)
│   │   └── utils/            # Utility functions (e.g., config, db, logging)
│   ├── Dockerfile            # Dockerfile for backend
│   ├── requirements.txt      # Python dependencies for backend
│   └── uvicorn_start.sh      # Script to start Uvicorn server
├── frontend/                 # Streamlit frontend application
│   ├── Dockerfile            # Dockerfile for frontend
│   ├── requirements.txt      # Python dependencies for frontend
│   └── streamlit_app.py      # Streamlit application script
├── data/                     # Directory for data ingestion (e.g., clinic information)
│   └── json/
├── cloudbuild.yaml           # Google Cloud Build configuration
├── docker-compose.yml        # Docker Compose configuration for multi-service deployment
├── LICENSE                   # Project license (MIT License)
└── README.md                 # This README file
```

## ⚠️ Important Disclaimer

This AI assistant is a demonstration project and uses only sample data.  
It is **not affiliated with any real clinic** and should not be relied upon for medical decisions.  
No Personally Identifiable Information (PII) is stored or retained by this application.

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.