# Integrati - Email & Calendar Manager

A modern, full-stack application for managing Gmail and Google Calendar integrations with comprehensive testing and CI/CD pipeline.

## 🚀 Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/integrati.git
   cd integrati
   ```

2. **Set up Firebase**
   - Go to [Firebase Console](https://console.firebase.google.com/)
   - Create a new project
   - Enable Authentication (Email/Password & Google)
   - Enable Firestore Database
   - In Project Settings > General > Your apps, get your Firebase config

3. **Set up Google OAuth**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create OAuth 2.0 credentials (Web application)
   - Add authorized redirect URIs:
     - `http://localhost:8000/integrations/gmail/auth/callback`
     - `http://localhost:8000/integrations/calendar/auth/callback`
   - Download credentials as `backend/app/credentials.json`

4. **Configure Environment**
   ```bash
   cp env.example .env
   ```
   Edit `.env` with your Firebase config:
   ```
   # Firebase
   REACT_APP_FIREBASE_API_KEY=your-api-key
   REACT_APP_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
   REACT_APP_FIREBASE_PROJECT_ID=your-project-id
   REACT_APP_FIREBASE_STORAGE_BUCKET=your-bucket.appspot.com
   REACT_APP_FIREBASE_MESSAGING_SENDER_ID=123456
   REACT_APP_FIREBASE_APP_ID=your-app-id

   # Backend
   BACKEND_URL=http://localhost:8000
   DATABASE_URL=sqlite:///./app.db
   GOOGLE_CLIENT_ID=your-google-client-id
   GOOGLE_CLIENT_SECRET=your-google-client-secret
   SECRET_KEY=your-secret-key
   ```

5. **Run with Docker**
   ```bash
   docker compose up --build
   ```
   The app will be available at http://localhost:3000

## 🧪 Testing & Quality Assurance

### Pre-commit Setup

Before making any commits, ensure you have the pre-commit hooks installed:

```bash
# Install pre-commit hooks
pre-commit install

# Run all checks manually
pre-commit run --all-files
```

### Backend Testing

The backend includes comprehensive unit tests with 72 test cases and 55% code coverage:

```bash
cd backend

# Run all tests
pytest tests/unit/ -v

# Run tests with coverage
pytest tests/unit/ -v --cov=app --cov-report=term-missing

# Run specific test categories
pytest tests/unit/models/ -v      # Model tests
pytest tests/unit/api/ -v         # API endpoint tests
pytest tests/unit/crud/ -v        # Database operation tests
pytest tests/unit/core/ -v        # Core functionality tests

# Run linting
ruff check app/
ruff format app/
```

### Frontend Testing

```bash
cd frontend

# Run tests
npm test

# Run linting
npm run lint
```

### Testing Before Push

**Always run these checks before pushing your code:**

1. **Backend Tests**
   ```bash
   cd backend
   pytest tests/unit/ -v --cov=app
   ```

2. **Linting & Formatting**
   ```bash
   ruff check app/ --fix
   ruff format app/
   ```

3. **Pre-commit Hooks**
   ```bash
   pre-commit run --all-files
   ```

4. **Frontend Tests** (if frontend changes)
   ```bash
   cd frontend
   npm test
   npm run lint
   ```

## 🔧 Features

- **Gmail Integration**
  - Search emails with advanced queries
  - Send and reply to emails
  - View email threads and conversations
  - Get last received email

- **Google Calendar**
  - View upcoming events
  - Create new events
  - Manage event attendees
  - Calendar synchronization

- **User Management**
  - Firebase Authentication
  - JWT token-based sessions
  - User integration tracking
  - Pending action approvals

## 🏗 Architecture

### Backend (FastAPI + SQLAlchemy)
- **FastAPI** - Modern, fast web framework
- **SQLAlchemy** - Database ORM with SQLite
- **Pydantic** - Data validation and settings
- **Firebase Admin SDK** - Authentication
- **Google APIs** - Gmail and Calendar integration

### Frontend (React)
- **React** - User interface
- **Firebase Auth** - Client-side authentication
- **Axios** - HTTP client for API calls

### Testing & Quality
- **Pytest** - Unit testing framework
- **Ruff** - Fast Python linter and formatter
- **Coverage** - Code coverage reporting
- **Pre-commit hooks** - Automated quality checks

## 🔒 Security

- All credentials stored in `.env` (not committed to git)
- Firebase Authentication for secure access
- OAuth2 for Google services
- JWT tokens for session management
- Input validation with Pydantic models

## 🚀 CI/CD Pipeline

### GitHub Actions Workflows

The project includes automated CI/CD pipelines:

1. **Backend Tests** (`.github/workflows/backend-tests.yml`)
   - Runs on every push to main
   - Executes all unit tests
   - Performs linting with Ruff
   - Security scanning with Bandit and Safety
   - Uploads coverage to Codecov

2. **Frontend Tests** (`.github/workflows/frontend-tests.yml`)
   - Runs on every push to main
   - Executes frontend tests
   - Performs linting
   - Uploads coverage to Codecov

### Local Development Workflow

```bash
# 1. Make your changes
# 2. Run tests
cd backend && pytest tests/unit/ -v

# 3. Run linting
ruff check app/ --fix

# 4. Stage changes
git add .

# 5. Commit (pre-commit hooks run automatically)
git commit -m "Your commit message"

# 6. Push (GitHub Actions run automatically)
git push origin main
```

## 📊 Test Coverage

Current test coverage: **55%** with 72 comprehensive tests covering:

- **Models** (100% coverage) - All Pydantic and SQLAlchemy models
- **CRUD Operations** (100% coverage) - Database operations
- **API Endpoints** (92% coverage) - Authentication and integration endpoints
- **Security Functions** (100% coverage) - JWT token management
- **Core Configuration** (100% coverage) - Settings and dependencies

## 🛠 Development

### Project Structure

```
├── frontend/                 # React frontend
│   ├── src/
│   │   ├── pages/           # Page components
│   │   ├── context/         # React context (Auth)
│   │   ├── services/        # API services
│   │   └── firebase.js      # Firebase configuration
│   ├── Dockerfile           # Frontend container
│   └── package.json
├── backend/                  # Python backend
│   ├── app/
│   │   ├── api/             # FastAPI routers
│   │   ├── core/            # Configuration and security
│   │   ├── crud/            # Database operations
│   │   ├── models/          # SQLAlchemy and Pydantic models
│   │   └── integrations/    # Gmail and Calendar integrations
│   ├── tests/               # Comprehensive test suite
│   │   ├── unit/            # Unit tests
│   │   │   ├── api/         # API endpoint tests
│   │   │   ├── core/        # Core functionality tests
│   │   │   ├── crud/        # Database operation tests
│   │   │   ├── models/      # Model validation tests
│   │   │   └── integrations/ # Integration tests
│   │   └── conftest.py      # Test configuration
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── requirements-test.txt # Test dependencies
│   └── pyproject.toml       # Ruff configuration
├── .github/workflows/       # CI/CD pipelines
├── docker-compose.yml       # Multi-container setup
└── .pre-commit-config.yaml  # Pre-commit hooks
```

### Running in Development Mode

For frontend development with hot reloading:

```bash
# Install dependencies in container
docker run --rm -v $(pwd)/frontend:/app -w /app node:18 npm install

# Start development server
docker run --rm -v $(pwd)/frontend:/app -w /app -p 3000:3000 node:18 npm start
```

For backend development:

```bash
cd backend

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-test.txt

# Run development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run tests in watch mode
pytest tests/unit/ -v --cov=app --cov-report=term-missing -f
```

## 📋 API Endpoints

### Authentication
- `POST /api/auth/firebase-token` - Firebase token exchange
- `GET /api/auth/me` - Get current user info

### Gmail Integration
- `GET /api/gmail/search` - Search emails
- `GET /api/gmail/last-received` - Get last received email
- `POST /api/gmail/send` - Send email

### Calendar Integration
- `GET /api/calendar/events` - Get calendar events
- `POST /api/calendar/events` - Create new event
- `DELETE /api/calendar/events/{event_id}` - Delete event

### Integration Management
- `GET /api/integrations` - List user integrations
- `POST /api/integrations` - Create integration
- `GET /api/pending-actions` - List pending actions

## 🔧 Troubleshooting

### Common Issues

1. **CORS Errors**
   - Ensure Firebase Auth domains include `localhost`
   - Check backend CORS configuration

2. **Database Issues**
   - Verify `DATABASE_URL` in environment
   - Check SQLite file permissions

3. **OAuth Errors**
   - Verify Google OAuth credentials
   - Check redirect URIs in Google Cloud Console

4. **Test Failures**
   - Ensure all dependencies installed: `pip install -r requirements-test.txt`
   - Check database connection in tests
   - Verify mock configurations

### Debug Commands

```bash
# Check Docker logs
docker compose logs backend
docker compose logs frontend

# Run backend in debug mode
cd backend && uvicorn app.main:app --reload --log-level debug

# Check test coverage
pytest tests/unit/ --cov=app --cov-report=html
# Open htmlcov/index.html in browser
```

## 🤝 Contributing

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes**
4. **Run tests and quality checks**
   ```bash
   cd backend && pytest tests/unit/ -v
   ruff check app/ --fix
   pre-commit run --all-files
   ```
5. **Commit your changes**
   ```bash
   git add .
   git commit -m "Add your feature description"
   ```
6. **Push and create a pull request**

### Code Quality Standards

- All code must pass Ruff linting
- All tests must pass (minimum 55% coverage)
- Pre-commit hooks must pass
- Follow PEP 8 style guidelines
- Include appropriate docstrings

## 📈 Monitoring & Analytics

- **Code Coverage**: Tracked via Codecov
- **Test Results**: Available in GitHub Actions
- **Security**: Automated scanning with Bandit and Safety
- **Performance**: Monitor via Docker logs and application metrics

## 📄 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- FastAPI for the excellent web framework
- Firebase for authentication services
- Google APIs for Gmail and Calendar integration
- Pytest for comprehensive testing
- Ruff for fast Python linting and formatting
