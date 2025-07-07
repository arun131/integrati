# Gmail & Calendar Manager Frontend (React)

This is the React frontend for the Gmail & Calendar Manager MVP. It provides a modern web interface for managing Gmail and Google Calendar integrations with Firebase authentication.

## Features
- Firebase authentication (Google, GitHub, Email/Password)
- Gmail integration (search, send, reply to emails)
- Google Calendar integration (view, create, delete events)
- JWT-based API communication with backend
- Responsive design with modern UI
- Protected routes with authentication
- Integration management dashboard

## Project Structure
```
frontend/
├── src/
│   ├── pages/                         # React page components
│   │   ├── LoginPage.js               # Authentication page
│   │   ├── DashboardPage.js           # Main dashboard
│   │   ├── AddIntegrationPage.js      # Add new integrations
│   │   ├── GmailIntegrationPage.js    # Gmail operations
│   │   ├── CalendarIntegrationPage.js # Calendar operations
│   │   ├── SendEmailPage.js           # Email composition
│   │   └── CreateEventPage.js         # Event creation
│   ├── context/                       # React context providers
│   │   └── AuthContext.js             # Authentication state management
│   ├── services/                      # API and external services
│   │   └── api.js                     # Axios configuration and interceptors
│   ├── styles/                        # CSS styles
│   │   └── index.css                  # Global styles
│   ├── App.js                         # Main app component with routing
│   ├── firebase.js                    # Firebase configuration
│   ├── index.js                       # App entry point
│   └── reportWebVitals.js             # Performance monitoring
├── public/                            # Static assets
├── package.json                       # Dependencies and scripts
├── Dockerfile                         # Docker build
├── nginx.conf                         # Nginx configuration
└── README.md                          # This file
```

## Code Flow

### Authentication Flow
1. **User** → LoginPage → Firebase Authentication (Google/GitHub/Email)
2. **Firebase** → Returns user object → AuthContext stores user
3. **AuthContext** → Exchanges Firebase token for JWT → Backend API
4. **Backend** → Returns JWT → AuthContext stores token
5. **App** → Redirects to Dashboard → Protected routes accessible

### Integration Flow
1. **User** → Dashboard → View existing integrations
2. **User** → AddIntegrationPage → Select integration type (Gmail/Calendar)
3. **User** → OAuth flow → Google authorization
4. **Backend** → Stores tokens → Integration created
5. **User** → Integration page → Use Gmail/Calendar features

### API Communication Flow
1. **Component** → Makes API call → Services/api.js
2. **api.js** → Adds JWT token → Request interceptor
3. **Backend** → Validates token → Returns data
4. **Component** → Receives response → Updates UI
5. **api.js** → Handles 401 errors → Redirects to login

## Setup (Local Development)

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Create environment variables:**
   Create a `.env.development` file with:
   ```
   REACT_APP_BACKEND_URL=http://localhost:8000
   REACT_APP_FIREBASE_API_KEY=your-firebase-api-key
   REACT_APP_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
   REACT_APP_FIREBASE_PROJECT_ID=your-project-id
   REACT_APP_FIREBASE_STORAGE_BUCKET=your-project.appspot.com
   REACT_APP_FIREBASE_MESSAGING_SENDER_ID=123456789
   REACT_APP_FIREBASE_APP_ID=your-app-id
   ```

3. **Start the development server:**
   ```bash
   npm start
   ```

## Running with Docker
1. **Build the Docker image:**
   ```bash
   docker build -t gmail-calendar-frontend .
   ```
2. **Run the container:**
   ```bash
   docker run -p 3000:80 gmail-calendar-frontend
   ```

## Key Components

### Pages
- **LoginPage** - Firebase authentication with multiple providers
- **DashboardPage** - Main dashboard showing user integrations
- **AddIntegrationPage** - Add new Gmail or Calendar integrations
- **GmailIntegrationPage** - Gmail operations (search, send, reply)
- **CalendarIntegrationPage** - Calendar operations (view, create, delete)
- **SendEmailPage** - Email composition interface
- **CreateEventPage** - Event creation interface

### Context
- **AuthContext** - Manages authentication state, Firebase user, and JWT tokens

### Services
- **api.js** - Axios configuration with JWT token injection and error handling

### Authentication
- Uses Firebase Authentication for initial login
- Exchanges Firebase tokens for backend JWTs
- Automatic token refresh and error handling
- Protected routes with authentication checks

## Environment Variables
Required environment variables:
- `REACT_APP_BACKEND_URL` - Backend API URL
- `REACT_APP_FIREBASE_API_KEY` - Firebase API key
- `REACT_APP_FIREBASE_AUTH_DOMAIN` - Firebase auth domain
- `REACT_APP_FIREBASE_PROJECT_ID` - Firebase project ID
- `REACT_APP_FIREBASE_STORAGE_BUCKET` - Firebase storage bucket
- `REACT_APP_FIREBASE_MESSAGING_SENDER_ID` - Firebase messaging sender ID
- `REACT_APP_FIREBASE_APP_ID` - Firebase app ID

## Dependencies
- **React** - UI framework
- **React Router** - Client-side routing
- **Firebase** - Authentication and database
- **Axios** - HTTP client for API calls
- **JWT Decode** - JWT token handling

## Notes
- **Never commit your `.env` files to git!**
- The frontend uses Firebase for authentication and Firestore for storing integration data
- All API calls include JWT tokens automatically via Axios interceptors
- Protected routes ensure users are authenticated before accessing features 