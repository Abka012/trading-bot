# Trading Bot Backend

FastAPI backend for the trading bot application.

## Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn main:app --reload
```

## API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Docker

```bash
# Build the image
docker build -t trading-bot-backend .

# Run the container
docker run -p 8000:8000 trading-bot-backend
```

## Development

- FastAPI with automatic API documentation
- CORS enabled for React frontend (`http://localhost:3000`)
- Uvicorn as ASGI server

## Requirements

- Python 3.9+
- See `requirements.txt` for dependencies
