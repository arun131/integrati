#!/bin/bash

# Integrati Backend Development Script with uv and Docker

set -e

echo "🚀 Integrati Backend Development Setup"

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "📁 Project root: $PROJECT_ROOT"
echo "📁 Backend directory: $SCRIPT_DIR"

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed. Please install uv first:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create data directory if it doesn't exist
echo "📁 Creating data directory..."
mkdir -p "$SCRIPT_DIR/data"

# Check for .env file in the root integrati directory
ROOT_ENV_FILE="$PROJECT_ROOT/.env"
ROOT_ENV_EXAMPLE="$PROJECT_ROOT/.env.example"

echo "🔍 Checking for environment file..."

if [ ! -f "$ROOT_ENV_FILE" ]; then
    if [ -f "$ROOT_ENV_EXAMPLE" ]; then
        echo "📋 Copying .env.example to .env in root directory..."
        cp "$ROOT_ENV_EXAMPLE" "$ROOT_ENV_FILE"
        echo "⚠️  Please edit $ROOT_ENV_FILE with your actual credentials"
    else
        echo "⚠️  No .env.example found in $PROJECT_ROOT"
        echo "📝 Creating basic .env file..."
        cat > "$ROOT_ENV_FILE" << EOF
# Integrati Backend Environment Configuration

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
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# Database Configuration
STORAGE_BACKEND=redis
DATABASE_URL=sqlite:///./data/mcp_plexus_data.sqlite3

# Server Configuration
HOST_APP_REGISTRATION_SECRET=your-host-app-secret
DEBUG_MODE=true
PLEXUS_FASTMCP_LOG_LEVEL=INFO
EOF
        echo "⚠️  Please edit $ROOT_ENV_FILE with your actual credentials"
    fi
else
    echo "✅ Environment file already exists at $ROOT_ENV_FILE"
fi

# Copy .env to backend directory for Docker
echo "📋 Copying .env to backend directory for Docker..."
cp "$ROOT_ENV_FILE" "$SCRIPT_DIR/.env"

# Build and start services with Docker Compose
echo "🐳 Building and starting services with Docker Compose..."
cd "$SCRIPT_DIR"

# Build the Docker image
echo "🔨 Building Docker image..."
docker-compose build

# Start the services
echo "🚀 Starting services..."
docker-compose up -d

echo "🎉 Setup complete!"
echo ""
echo "📋 Services running:"
echo "  - Redis: localhost:6379"
echo "  - Backend: http://localhost:8000"
echo ""
echo "📋 Useful commands:"
echo "  - View logs: docker-compose logs -f"
echo "  - Stop services: docker-compose down"
echo "  - Restart services: docker-compose restart"
echo "  - Rebuild and restart: docker-compose up --build -d"
echo ""
echo "🔍 Checking service health..."
sleep 5

# Check if services are healthy
if docker-compose ps | grep -q "healthy"; then
    echo "✅ All services are healthy!"
else
    echo "⚠️  Some services may still be starting up..."
    echo "📊 Service status:"
    docker-compose ps
fi
