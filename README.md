# Integrati - Integration Management Platform

A modern web application that allows users to connect and manage multiple service integrations like Gmail and Google Calendar through a unified interface.

## Features

- **Firebase Authentication**: Sign in with email/password, Google, or GitHub
- **Integration Management**: Add and manage multiple service integrations
- **Gmail Integration**: Search emails, send emails, reply to emails
- **Google Calendar Integration**: View events, create events, manage calendar
- **Modern UI**: Clean, responsive design with intuitive navigation

## Tech Stack

- **Frontend**: React.js with Firebase Authentication
- **Backend**: Python (FastAPI)
- **Database**: Firebase Firestore
- **Containerization**: Docker & Docker Compose

## Prerequisites

- Docker and Docker Compose installed
- Firebase project with Authentication and Firestore enabled
- Google Cloud Console project for OAuth credentials

## Setup Instructions

### 1. Firebase Setup

1. Create a new Firebase project at [Firebase Console](https://console.firebase.google.com/)
2. Enable Authentication with Email/Password, Google, and GitHub providers
3. Enable Firestore Database
4. Get your Firebase configuration from Project Settings > General > Your apps

### 2. Environment Configuration

1. Copy the example environment file:
   ```bash
   cp env.example .env
   ```

2. Update `.env` with your actual credentials:
   ```bash
   # Firebase Configuration
   REACT_APP_FIREBASE_API_KEY=your-actual-firebase-api-key
   REACT_APP_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
   REACT_APP_FIREBASE_PROJECT_ID=your-project-id
   REACT_APP_FIREBASE_STORAGE_BUCKET=your-project.appspot.com
   REACT_APP_FIREBASE_MESSAGING_SENDER_ID=123456789
   REACT_APP_FIREBASE_APP_ID=your-app-id

   # Backend Configuration
   DATABASE_URL=your-database-url
   GOOGLE_CLIENT_ID=your-google-client-id
   GOOGLE_CLIENT_SECRET=your-google-client-secret
   SECRET_KEY=your-secret-key
   ```

### 3. Run the Application

1. Build and start the containers:
   ```bash
   docker-compose up --build
   ```

2. Access the application:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000

### 4. First Time Setup

1. Open http://localhost:3000 in your browser
2. Sign up or sign in using your preferred method (email, Google, or GitHub)
3. Add your first integration (Gmail or Google Calendar)
4. Grant necessary permissions when prompted
5. Start using the integration features!

## Development

### Running in Development Mode

For frontend development with hot reloading:

```bash
# Install dependencies in container
docker run --rm -v $(pwd)/frontend:/app -w /app node:18 npm install

# Start development server
docker run --rm -v $(pwd)/frontend:/app -w /app -p 3000:3000 node:18 npm start
```

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
│   ├── Dockerfile
│   └── requirements.txt
├── docker-compose.yml       # Multi-container setup
└── env.example             # Environment variables template
```

## API Endpoints

### Authentication
- `POST /auth/google/gmail` - Gmail OAuth flow
- `POST /auth/google/calendar` - Calendar OAuth flow

### Gmail Integration
- `GET /gmail/last-received` - Get last received email
- `POST /gmail/search` - Search emails
- `POST /gmail/send` - Send email

### Calendar Integration
- `GET /calendar/events` - Get calendar events
- `POST /calendar/events` - Create new event

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License.
