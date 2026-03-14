# Trading Bot

A modern trading bot application built with React (frontend) and FastAPI (backend).

## Project Structure

```
trading-bot/
├── frontend/          # React frontend application
├── backend/           # FastAPI backend application
├── .gitignore
└── README.md
```

## Prerequisites

- Node.js 18+ and npm
- Python 3.9+
- Docker (optional, for deployment)

## Quick Start

### Frontend

```bash
cd frontend
npm install
npm start
```

The frontend will run on `http://localhost:3000`

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

The backend API will be available at `http://localhost:8000`

## Docker Deployment

```bash
cd backend
docker build -t trading-bot-backend .
docker run -p 8000:8000 trading-bot-backend
```

## Development

- Frontend: React with modern hooks and Axios for API calls
- Backend: FastAPI with CORS enabled for frontend communication
- API Documentation: Available at `http://localhost:8000/docs`

## License

MIT
