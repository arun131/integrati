#!/bin/bash

# Integrati - Complete Fresh Start Script
# This script removes ALL stored data and starts the application from scratch
# WARNING: This will delete all users, data, and configurations!
# Usage: ./fresh-start.sh [-d] where -d enables detached mode

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

echo "⚠️  WARNING: This will delete ALL stored data!"
echo "   - All user accounts will be lost"
echo "   - All integration data will be lost"
echo "   - All OAuth tokens will be lost"
echo "   - All analytics data will be lost"
echo "   - Requires sudo permissions to remove protected files"
echo ""

# Ask for sudo password
echo "🔐 This operation requires sudo permissions to remove all data."
echo "   Please enter your sudo password when prompted."
echo ""

# Check if user has sudo access
if ! sudo -n true 2>/dev/null; then
    echo "🔐 Please enter your sudo password:"
    sudo -v
    if [ $? -ne 0 ]; then
        echo "❌ Sudo access denied. Cannot proceed with cleanup."
        exit 1
    fi
fi

echo ""
echo "🧹 Starting COMPLETE fresh data cleanup..."

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

# Stop all services and remove volumes (this removes Redis data)
echo "🛑 Stopping services and removing all data..."
docker compose down -v

# Remove database files
echo "🗑️  Removing database files..."
sudo rm -f integrati_backend/data/*.sqlite3
sudo rm -f integrati_backend/data/*.db

# Remove cache directories
echo "🧹 Removing cache directories..."
sudo rm -rf integrati_backend/__pycache__/
sudo rm -rf integrati_backend/.ruff_cache/
sudo rm -rf integrati_backend/.pytest_cache/
sudo rm -rf integrati_backend/.coverage
sudo rm -rf integrati_backend/integrati_backend.egg-info/
sudo rm -rf .ruff_cache/
sudo rm -rf .pytest_cache/
sudo rm -rf .venv/
sudo rm -rf node_modules/

# CRITICAL: Remove the entire data directory to clear ALL SQLite tables
echo "🗑️  Removing entire data directory (clears all tables)..."
sudo rm -rf integrati_backend/data/

# Recreate the data directory
echo "📁 Recreating data directory..."
sudo mkdir -p integrati_backend/data
# Fix ownership back to current user
sudo chown $(whoami):$(id -gn) integrati_backend/data

echo ""
echo "✨ COMPLETE cleanup finished!"
echo ""

# Ask if user wants to start services now
read -p "Do you want to start the services now? (y/n): " start_now

if [[ $start_now =~ ^[Yy]$ ]]; then
    echo ""
    echo "🚀 Starting fresh services..."

    if [ "$DETACHED_MODE" = true ]; then
        echo "🔄 Starting in DETACHED mode (running in background)..."
        docker compose up --build -d

        # Wait for services to start
        echo "⏳ Waiting for services to be ready..."
        sleep 10

        # Show service status
        echo ""
        echo "📊 Service Status:"
        docker compose ps

        echo ""
        echo "🌐 Your application is now running at:"
        echo "   Frontend: http://localhost:3000"
        echo "   Backend:  http://localhost:8000"
        echo "   Redis:    localhost:6380"
        echo ""
        echo "🎉 Fresh start complete! All data has been cleared."
        echo "   Services are running in the background."
    else
        echo "📺 Starting in ATTACHED mode (you'll see live logs)..."
        echo "🌐 Your application will be available at:"
        echo "   Frontend: http://localhost:3000"
        echo "   Backend:  http://localhost:8000"
        echo "   Redis:    localhost:6380"
        echo ""
        echo "🎉 Fresh start complete! All data has been cleared."
        echo "   Starting services with live logs visible..."
        docker compose up --build
        # Note: In attached mode, this line won't execute until you stop with Ctrl+C
    fi
else
    echo ""
    echo "📋 To start services later, run:"
    echo "   ./start.sh"
    echo ""
    echo "✅ Fresh start cleanup complete!"
fi

echo ""
echo "📋 Useful commands:"
echo "   Normal start:  ./start.sh"
echo "   Normal start (detached): ./start.sh -d"
echo "   Fresh start:   ./fresh-start.sh"
echo "   Fresh start (detached): ./fresh-start.sh -d"
echo "   View logs:     docker compose logs -f"
echo "   Stop services: docker compose down"
