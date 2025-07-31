#!/bin/bash

# Integrati Backend Local Development Script with uv

set -e

echo "🚀 Integrati Backend Local Development Setup"

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
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# Database Configuration
STORAGE_BACKEND=sqlite
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

# Change to backend directory
cd "$SCRIPT_DIR"

# Create virtual environment and install dependencies with uv
echo "🐍 Setting up Python virtual environment with uv..."
uv venv

# Install dependencies
echo "📦 Installing dependencies with uv..."
uv pip install -r requirements.txt

echo "🎉 Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Edit $ROOT_ENV_FILE with your actual credentials"
echo "2. Start Redis server: redis-server"
echo "3. Run the development server: uv run python run_dev.py"
echo ""
echo "🚀 Starting development server..."
uv run python run_dev.py
