# Integrati - Email & Calendar Manager

A simple Docker-based application to manage Gmail and Google Calendar integrations.

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
   ```

5. **Run with Docker**
   ```bash
   docker compose up --build
   ```
   The app will be available at http://localhost:3000

## 🔧 Features

- **Gmail Integration**
  - Search emails
  - Send and reply to emails
  - View email threads

- **Google Calendar**
  - View upcoming events
  - Create new events
  - Manage event attendees

## 🔒 Security

- All credentials are stored in `.env` (not committed to git)
- Uses Firebase Authentication for secure access
- OAuth2 for Google services

## 🛠 Troubleshooting

- If you get CORS errors, ensure your Firebase Auth domains include `localhost`
- Check Docker logs with `docker compose logs`
- Clear browser cache if you encounter stale data issues

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
