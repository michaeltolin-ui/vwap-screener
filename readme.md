# VWAP Snapback Screener

A full-stack stock screener for VWAP snapback signals using Streamlit, FastAPI, and Redis.

## Setup
### Prerequisites
- Docker and Docker Compose
- Python 3.9+ (for local development)
- Git

### Local Development
1. Clone: `git clone <repository-url>`
2. Install: `pip install -r requirements.txt`
3. Run Redis: `redis-server`
4. Run FastAPI: `uvicorn main:app --host 0.0.0.0 --port 8000`
5. Run Streamlit: `streamlit run app.py`
6. Access: `http://localhost:8501`

### Docker
1. Clone: `git clone <repository-url>`
2. Run: `docker-compose up --build`
3. Access: `http://localhost:8501` (Streamlit), `http://localhost:8000/docs` (FastAPI)

## Notes
- Replace `fetch_stock_data` in `main.py` with real API (e.g., Yahoo Finance).
- Configure API credentials for live data.
- For production, secure Redis and use cloud hosting.
