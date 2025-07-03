# Gmail & Calendar Manager Backend (FastAPI)

This is the FastAPI backend for the Gmail & Calendar Manager MVP. It provides secure Google OAuth2 login, Gmail API operations (search, get last email, send, reply), and JWT-based authentication for the frontend.

## Features
- Google OAuth2 login (secure, with refresh token storage)
- Search Gmail inbox
- Get last received email
- Send new email
- Reply to previous email
- JWT session management
- SQLite database for user/token storage
- Dockerized for easy deployment (Google Cloud Run ready)

## Project Structure
```
backend/
├── app/
│   ├── api/           # FastAPI routers (auth, gmail)
│   ├── core/          # Config, security, dependencies
│   ├── crud/          # Database CRUD operations
│   ├── database/      # DB connection
│   ├── models/        # SQLAlchemy & Pydantic models
│   └── services/      # Google API logic
├── requirements.txt   # Python dependencies
├── Dockerfile         # Docker build
├── .env.example       # Example environment variables
└── README.md          # This file
```

## Setup (Local Development)

1. **Clone the repository** and `cd backend`.
2. **Create a virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Create `.env` file:**
   - Copy `.env.example` to `.env` and fill in your Google OAuth credentials, secret key, and frontend URL.
5. **Add Google OAuth credentials:**
   - Download `credentials.json` from Google Cloud Console and place it in `backend/app/`.
6. **Run the backend:**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## Running with Docker
1. **Build the Docker image:**
   ```bash
   docker build -t my-gmail-backend-mvp .
   ```
2. **Run the container:**
   ```bash
   docker run -p 8000:8000 --env-file .env my-gmail-backend-mvp
   ```

## Environment Variables
See `.env.example` for all required variables:
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`
- `SECRET_KEY`, `FRONTEND_URL`

## API Endpoints
- `GET /auth/google/login` — Initiate Google OAuth2 login
- `GET /auth/google/callback` — OAuth2 callback
- `GET /auth/me` — Get current user info (JWT required)
- `POST /gmail/search` — Search emails (JWT required)
- `GET /gmail/last-received` — Get last email (JWT required)
- `POST /gmail/send` — Send or reply to email (JWT required)

## Deployment (Google Cloud Run)
- Build and push Docker image to Google Container Registry
- Deploy to Cloud Run, set environment variables in the service config
- Update Google Cloud Console with your Cloud Run callback URL

## Notes
- **Never commit your `.env` or `credentials.json` to git!**
- Update CORS origins in `main.py` for production.
- For full setup, see the main project README or deployment guide. 