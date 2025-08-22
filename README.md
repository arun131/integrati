# Integrati - Agentic Personal Assistant

A modern application for managing Gmail and Google Calendar integrations with AI-powered email management.

## 🚀 Quick Start

### 1. Prerequisites
- **Docker & Docker Compose** installed on your system
- **Firebase project** with authentication enabled (get it from Arun)
- **Google Cloud project** with Gmail and Calendar APIs enabled (get it from Arun)

### 2. Setup
```bash
# Clone the repository
git clone <your-repo-url>
cd integrati

# Copy environment file
cp env.example .env
```

### 3. Configuration Files (get them from Arun)
You'll need these files from the project maintainer:
- `.env` - Environment variables (copy from `env.example` and fill in your values)
- `integrati_backend/firebase-service-account.json` - Firebase service account key
- `integrati_backend/integrati-app-pubsub-loginkey.json` - Google Cloud service account key

### 4. Start the Application

#### **Normal Start (Keep Data):**
```bash
./start.sh
```

#### **Fresh Start (Clear All Data):**
```bash
./fresh-start.sh
```
**Note:** Requires sudo permissions to remove protected files.

#### **Detached Mode (Background):**
```bash
./start.sh -d
./fresh-start.sh -d
```

#### **Debug Mode (VS Code/Cursor Remote Debugging):**
```bash
docker compose -f docker-compose.debug.yml up --build
```
Then in VS Code/Cursor:
1. Go to **Run and Debug** section
2. Select **Remote Attach (Docker)**
3. Start debugging your Python backend

**Note:** Debug mode includes Cloudflare tunnel setup for Google push notifications.

### 5. Access the App
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **Redis**: localhost:6380

## 📋 What You Get

- **Gmail Integration**: Search, send, and manage emails
- **Calendar Management**: View and create calendar events
- **AI-Powered**: Smart email processing and responses
- **Multi-tenant**: Support for multiple organizations
- **Real-time**: Push notifications for new emails

## 🛠 Development

### **View Logs:**
```bash
docker compose logs -f
```

### **Stop Services:**
```bash
docker compose down
```

### **Restart with Code Changes:**
```bash
./start.sh  # Always rebuilds with latest code
```

### **Debug Mode:**
```bash
# Start debug services
docker compose -f docker-compose.debug.yml up --build

# In VS Code/Cursor: Run and Debug → Remote Attach (Docker)
```

## 🔧 Troubleshooting

- **Docker not running**: Start Docker Desktop or Docker service
- **Port conflicts**: Check if ports 3000, 8000, or 6380 are available
- **Permission errors**: Make scripts executable with `chmod +x *.sh`

## 📁 Project Structure

```
├── frontend/                 # React frontend
├── integrati_backend/        # Python backend (FastAPI)
├── docker-compose.yml        # Docker configuration
├── start.sh                  # Start/restart script
├── fresh-start.sh            # Fresh start script
└── .env                      # Environment configuration
```

## 🆘 Need Help?

1. Check that Docker is running
2. Verify you're in the correct directory
3. Ensure all configuration files are in place
4. Check `docker compose logs` for error messages

---

**That's it!** The scripts handle everything else automatically. 🎉
