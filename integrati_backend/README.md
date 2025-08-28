# Integrati Backend

A multi-tenant, multi-user MCP (Model Context Protocol) backend system with integrations for Gmail, Calendar, and some common tools.

## 🚀 Features

- **Multi-user Architecture**: Support for multiple independent users
- **Multi-config Support**: Config management per user with Firebase authentication
- **MCP Protocol**: Full MCP server implementation with FastMCP 2.10
- **Integration Framework**: Extensible integration system for external services
- **OAuth Support**: Secure OAuth 2.0 flows for Gmail and Calendar
- **Analytics**: Comprehensive logging and analytics system
- **Docker Support**: Containerized deployment with Docker Compose

## 🏗️ Architecture

```
integrati_backend/
├── mcp_plexus/           # Core MCP server implementation
├── integrations/         # External service integrations
│   ├── common/           # Math tools (add, subtract, etc.)
│   ├── gmail/            # Gmail API integration
│   └── calendar/         # Google Calendar integration
├── frontend_integration/ # Frontend API endpoints
├── analytics/            # Analytics and logging system
└── data/                 # Persistent data storage
```

## 🛠️ Development Setup

### Prerequisites

- **Docker & Docker Compose** (for containerized development)
- **python 3.12 or above** (for local development):
- **install uv for python package management**: `pip install uv`
- **Redis** (for local development): included in the docker compose setup

### Quick Start with Docker (Recommended)

To quickly start the backend using Docker, ensure you have Docker and Docker Compose installed.

1. **Clone the repository and navigate to the project root:**
   ```bash
   git clone <repo-url>
   cd integrati_backend
   ```

2. **Build and start the backend and dependencies using Docker Compose:**
   ```bash
   docker compose up --build
   ```

   This command will:
   - Build the backend image using the provided `Dockerfile` in the `integrati_backend` directory
   - Start all required services (including Redis) as defined in your `docker-compose.yml`

3. **Access the backend API:**
   - Open [http://localhost:8000](http://localhost:8000) in your browser or API client.
   - API Docs [http://localhost:8000/docs](http://localhost:8000/docs)

4. **To stop the services:**
   ```bash
   docker compose down
   ```

_The Dockerfile in the `integrati_backend` folder is used to build the backend service image. All dependencies and environment setup are handled automatically by Docker Compose._

### Developer Start with python

1. **Clone and navigate to the project**:
   ```bash
   cd integrati_backend
   ```

2. **Run the development setup**:
   ```bash
   ./dev.sh
   ```

   This will:
   - Check for required tools (Docker, uv)
   - Create environment files
   - Build and start services with Docker Compose
   - Start Redis and the backend server

3. **Access the services**:
   - Backend API: http://localhost:8000
   - Redis: localhost:6379

### Local Development with uv

1. **Install uv and setup virtual env** (if not already installed):
   ```bash
   pip install uv
   uv venv
   source .venv/bin/activate
   ```

2. **Run local development setup**:
   ```bash
   ./dev-local.sh
   ```

   This will:
   - Create a Python virtual environment with uv
   - Install dependencies
   - Set up environment files
   - Start the development server

3. **Start Redis** (in a separate terminal):
   ```bash
   redis-server
   ```

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the root `integrati` directory with the following variables:

```bash
# Firebase Configuration
FIREBASE_PROJECT_ID=your-firebase-project-id
FIREBASE_PRIVATE_KEY_ID=your-private-key-id
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nYour private key here\n-----END PRIVATE KEY-----\n"
FIREBASE_CLIENT_EMAIL=your-service-account@your-project.iam.gserviceaccount.com
FIREBASE_CLIENT_ID=your-client-id
FIREBASE_AUTH_URI=https://accounts.google.com/o/oauth2/auth
FIREBASE_TOKEN_URI=https://oauth2.googleapis.com/token
FIREBASE_AUTH_PROVIDER_X509_CERT_URL=https://www.googleapis.com/oauth2/v1/certs
FIREBASE_CLIENT_X509_CERT_URL=https://www.googleapis.com/robot/v1/metadata/x509/your-service-account%40your-project.iam.gserviceaccount.com

# Gmail OAuth Configuration
GMAIL_CLIENT_ID=your-gmail-client-id
GMAIL_CLIENT_SECRET=your-gmail-client-secret
GMAIL_REDIRECT_URI=http://localhost:8000/api/integrations/gmail/callback

# Calendar OAuth Configuration
CALENDAR_CLIENT_ID=your-calendar-client-id
CALENDAR_CLIENT_SECRET=your-calendar-client-secret
CALENDAR_REDIRECT_URI=http://localhost:8000/api/integrations/calendar/callback

# Redis Configuration
REDIS_HOST=localhost  # Use 'redis' for Docker setup
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# Database Configuration
STORAGE_BACKEND=sqlite  # Use 'redis' for Docker setup
DATABASE_URL=sqlite:///./data/mcp_plexus_data.sqlite3

# Server Configuration
HOST_APP_REGISTRATION_SECRET=your-host-app-secret
DEBUG_MODE=true
PLEXUS_FASTMCP_LOG_LEVEL=INFO
```

### Getting Credentials

#### Firebase Setup
1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Create a new project or select existing one
3. Go to Project Settings > Service Accounts
4. Generate a new private key (JSON file)
5. Extract values from the JSON file

#### Gmail OAuth Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Gmail API
4. Go to APIs & Services > Credentials
5. Create OAuth 2.0 Client ID
6. Add authorized redirect URIs

#### Calendar OAuth Setup
1. In the same Google Cloud project
2. Enable Google Calendar API
3. Create another OAuth 2.0 Client ID for Calendar
4. Add authorized redirect URIs

## 📡 API Endpoints

### Authentication
- `POST /api/auth/firebase-token` - Exchange Firebase token for session
- `GET /api/auth/me` - Get current user info
- `POST /api/auth/logout` - Logout user

### Integrations
- `GET /api/integrations` - List user integrations
- `POST /api/integrations/{name}/auth` - Start OAuth flow
- `GET /api/integrations/{name}/callback` - OAuth callback
- `DELETE /api/integrations/{name}` - Remove integration
- `GET /api/integrations/{name}/status` - Get integration status

### Analytics
- `GET /api/analytics/summary` - Get analytics summary
- `GET /api/analytics/user` - Get user analytics
- `GET /api/analytics/tools` - Get tool usage analytics
- `GET /api/analytics/clients` - Get client usage analytics
- `GET /api/analytics/integrations` - Get integration usage analytics

### MCP Endpoints
- `GET /{username}/mcp` - MCP server endpoint for user

## 🐳 Docker Commands

### Development
```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild and restart
docker-compose up --build -d

# Access container shell
docker-compose exec integrati-backend bash
```

### Production
```bash
# Build production image
docker build -t integrati-backend .

# Run with environment variables
docker run -p 8000:8000 --env-file .env integrati-backend
```

## 🧪 Testing

### Run tests with uv
```bash
uv run pytest
```

### Run specific test file
```bash
uv run pytest tests/test_integrations.py
```

## 📊 Monitoring

### Health Checks
- Backend: `GET /health`
- Redis: `redis-cli ping`

### Logs
- Application logs are available via Docker Compose
- Analytics data is stored in SQLite database
- Redis provides session and token storage

## 🔍 Troubleshooting

### Common Issues

1. **Redis Connection Failed**
   - Ensure Redis is running: `redis-server`
   - Check Redis configuration in `.env`

2. **OAuth Callback Errors**
   - Verify redirect URIs in Google Cloud Console
   - Check OAuth client credentials

3. **Import Errors**
   - Ensure all dependencies are installed: `uv pip install -r requirements.txt`
   - Check Python path and virtual environment

4. **Docker Build Failures**
   - Clear Docker cache: `docker system prune`
   - Rebuild without cache: `docker-compose build --no-cache`

### Debug Mode
Set `DEBUG_MODE=true` in your `.env` file for detailed logging.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
