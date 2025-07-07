# Gmail & Calendar Manager Backend (FastAPI)

This is the FastAPI backend for the Gmail & Calendar Manager MVP. It provides Firebase authentication, Gmail API operations (search, get last email, send, reply), and Google Calendar operations (view, create, delete events) with JWT-based authentication for the frontend.

## Features
- Firebase authentication integration
- Gmail API operations (search, get last email, send, reply)
- Google Calendar operations (view, create, delete events)
- JWT session management
- SQLite database for user/token storage
- Dockerized for easy deployment

## Project Structure
```
backend/
├── app/
│   ├── api/                      # Core API routers (auth)
│   ├── core/                     # Config, security, dependencies
│   ├── crud/                     # Database CRUD operations
│   ├── database/                 # DB connection
│   ├── models/                   # SQLAlchemy & Pydantic models
│   └── integrations/             # Google API integrations
│       ├── gmail/                # Gmail API logic
│       │   ├── api.py            # Gmail API endpoints
│       │   ├── auth.py           # Gmail OAuth handling
│       │   └── google_auth.py    # Google credentials management
│       └── calendar/             # Calendar API logic
│           ├── api.py            # Calendar API endpoints
│           ├── auth.py           # Calendar OAuth handling
│           └── google_auth.py    # Google credentials management
├── requirements.txt              # Python dependencies
├── Dockerfile                    # Docker build
├── firebase-service-account.json # Firebase service account
└── README.md                     # This file
```

## Code Flow

### Authentication Flow
1. **Frontend** → Firebase Authentication → Gets Firebase ID token
2. **Frontend** → Backend `/api/auth/firebase-token` → Exchanges Firebase token for JWT
3. **Backend** → Verifies Firebase token → Creates/updates user in database → Returns JWT
4. **Frontend** → Uses JWT for subsequent API calls

### Gmail Integration Flow
1. **User** → Frontend → Initiates Gmail OAuth via `/integrations/gmail/auth/login`
2. **Google** → Redirects to `/integrations/gmail/auth/callback` → Stores tokens in database
3. **Frontend** → Calls Gmail API endpoints with JWT:
   - `POST /integrations/gmail/api/search` - Search emails
   - `GET /integrations/gmail/api/last-received` - Get last email
   - `POST /integrations/gmail/api/send` - Send/reply to email

### Calendar Integration Flow
1. **User** → Frontend → Initiates Calendar OAuth via `/integrations/calendar/auth/login`
2. **Google** → Redirects to `/integrations/calendar/auth/callback` → Stores tokens in database
3. **Frontend** → Calls Calendar API endpoints with JWT:
   - `GET /integrations/calendar/api/events` - Get calendar events
   - `POST /integrations/calendar/api/events` - Create new event
   - `DELETE /integrations/calendar/api/events/{event_id}` - Delete event

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
4. **Set up Firebase:**
   - Place your `firebase-service-account.json` in the backend directory
   - Or set `FIREBASE_SERVICE_ACCOUNT_JSON` environment variable
5. **Create `.env` file:**
   - Copy `.env.example` to `.env` and fill in your configuration
6. **Run the backend:**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## Running with Docker
1. **Build the Docker image:**
   ```bash
   docker build -t gmail-calendar-backend .
   ```
2. **Run the container:**
   ```bash
   docker run -p 8000:8000 --env-file .env gmail-calendar-backend
   ```

## Environment Variables
Required environment variables:
- `FIREBASE_SERVICE_ACCOUNT_PATH` or `FIREBASE_SERVICE_ACCOUNT_JSON` - Firebase credentials
- `SECRET_KEY` - JWT secret key
- `FRONTEND_URL` - Frontend URL for CORS
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` - Google OAuth credentials

## API Endpoints

### Authentication
- `POST /api/auth/firebase-token` — Exchange Firebase token for JWT
- `GET /api/auth/me` — Get current user info (JWT required)

### Gmail Integration
- `GET /integrations/gmail/auth/login` — Initiate Gmail OAuth
- `GET /integrations/gmail/auth/callback` — Gmail OAuth callback
- `POST /integrations/gmail/api/search` — Search emails (JWT required)
- `GET /integrations/gmail/api/last-received` — Get last email (JWT required)
- `POST /integrations/gmail/api/send` — Send or reply to email (JWT required)

### Calendar Integration
- `GET /integrations/calendar/auth/login` — Initiate Calendar OAuth
- `GET /integrations/calendar/auth/callback` — Calendar OAuth callback
- `GET /integrations/calendar/api/events` — Get calendar events (JWT required)
- `POST /integrations/calendar/api/events` — Create new event (JWT required)
- `DELETE /integrations/calendar/api/events/{event_id}` — Delete event (JWT required)

## Key Components

### Core Modules
- **`app/core/`** - Configuration, security, and dependency injection
- **`app/models/`** - Database models and Pydantic schemas
- **`app/database/`** - Database connection and session management
- **`app/crud/`** - Database operations for users and tokens

### Integration Modules
- **`app/integrations/gmail/`** - Complete Gmail API integration
- **`app/integrations/calendar/`** - Complete Calendar API integration
- Each integration has its own OAuth flow and API endpoints

### Authentication
- Uses Firebase for initial authentication
- JWT tokens for API authorization
- Automatic token refresh for Google APIs

## Notes
- **Never commit your `.env` or `firebase-service-account.json` to git!**
- Update CORS origins in `main.py` for production.
- The backend supports both Gmail and Calendar integrations with separate OAuth flows. 