#!/bin/bash

# Integrati - Normal Start/Restart Script
# This script starts or restarts the application WITHOUT losing any stored data
# Usage: ./start.sh [-d] where -d enables detached mode

set -e  # Exit on any error

# Parse command line arguments
DETACHED_MODE=false
while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--detached)
            DETACHED_MODE=true
            shift
            ;;
        *)
            echo "❌ Unknown option: $1"
            echo "Usage: $0 [-d|--detached]"
            exit 1
            ;;
    esac
done

echo "🚀 Starting Integrati application..."
if [ "$DETACHED_MODE" = true ]; then
    echo "🔄 Detached mode enabled (services will run in background)"
else
    echo "📺 Attached mode enabled (you'll see live logs, Ctrl+C to stop)"
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Please run this script from the root integrati directory (where docker-compose.yml is located)"
    exit 1
fi



# Function to check if services are running
check_services() {
    if docker compose ps | grep -q "Up"; then
        return 0
    else
        return 1
    fi
}

# Check if services are already running
if check_services; then
    echo "🔄 Services are running. Restarting with latest code changes..."
    docker compose down

    if [ "$DETACHED_MODE" = true ]; then
        echo "🔄 Starting in DETACHED mode (running in background)..."
        docker compose up --build -d
        echo "✅ Services restarted successfully with latest code!"
    else
        echo "📺 Starting in ATTACHED mode (you'll see live logs)..."
        docker compose up --build
        # Note: In attached mode, this line won't execute until you stop with Ctrl+C
    fi
else
    echo "🆕 Starting services for the first time..."

    if [ "$DETACHED_MODE" = true ]; then
        echo "🔄 Starting in DETACHED mode (running in background)..."
        docker compose up --build -d
        echo "✅ Services started successfully!"
    else
        echo "📺 Starting in ATTACHED mode (you'll see live logs)..."
        docker compose up --build
        # Note: In attached mode, this line won't execute until you stop with Ctrl+C
    fi
fi

# Wait a moment for services to fully start (only in detached mode)
if [ "$DETACHED_MODE" = true ]; then
    echo "⏳ Waiting for services to be ready..."
    sleep 5

    # Show service status
    echo ""
    echo "📊 Service Status:"
    docker compose ps
else
    echo ""
    echo "📺 Services are running in attached mode. You can see live logs above."
    echo "   Press Ctrl+C to stop the services when you're done."
fi

echo ""
echo "🌐 Your application is now running at:"
echo "   Frontend: http://localhost:3000"
echo "   Backend:  http://localhost:8000"
echo "   Redis:    localhost:6380"
echo ""
echo "📋 Useful commands:"
echo "   View logs:     docker compose logs -f"
echo "   Stop services: docker compose down"
echo "   Restart:       ./start.sh"
echo "   Restart (detached): ./start.sh -d"
echo "   Fresh start:   ./fresh-start.sh"
echo ""
if [ "$DETACHED_MODE" = true ]; then
    echo "🎉 Services are running in the background!"
    echo "   Use 'docker compose logs -f' to see logs"
else
    echo "🎉 Services are running with live logs visible!"
    echo "   Press Ctrl+C to stop when you're done"
fi
