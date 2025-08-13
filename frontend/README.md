# Integrati Frontend (React)

This is the React frontend for the Integrati project. It provides a modern web interface for managing integrations with Firebase authentication and a tenant-level OAuth architecture.

## Features
- Firebase authentication (Google, GitHub, Email/Password)
- **NEW**: Automatic tenant registration and management
- **NEW**: Tenant-level OAuth token sharing across configurations
- Gmail integration (search, send, reply to emails)
- Google Calendar integration (view, create, delete events)
- **NEW**: Persistent MCP tool registration per tenant
- **NEW**: Common tools available to all users (Calculator, Text Processor)
- **NEW**: Integration-specific tools (visible only when connected)
- JWT-based API communication with backend
- Responsive design with modern UI
- Protected routes with authentication
- Integration management dashboard with visual status indicators

## New Tenant-Level Architecture

This frontend now works with the new `integrati_backend` which implements a tenant-level OAuth system:
- **One human user = One tenant** with multiple configs/profiles
- **OAuth tokens shared** across all configs within a tenant
- **Automatic tenant registration** when users first log in
- **Persistent data** across server restarts
- **MCP tool registration** per tenant for AI assistant integration

## Environment Setup

**The frontend uses the root `.env` file** - no separate frontend environment file is needed.

Ensure the root `env.example` is copied to `.env` in the project root and configured with:

```bash
# Frontend Configuration (in root .env file)
REACT_APP_BACKEND_URL=http://localhost:8000
REACT_APP_ADMIN_API_KEY=your-admin-api-key-change-this-in-production
REACT_APP_DEBUG=true

# Firebase Configuration for Frontend
REACT_APP_FIREBASE_API_KEY=your-firebase-api-key
REACT_APP_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
REACT_APP_FIREBASE_PROJECT_ID=your-firebase-project-id
REACT_APP_FIREBASE_STORAGE_BUCKET=your-project.appspot.com
REACT_APP_FIREBASE_MESSAGING_SENDER_ID=123456789
REACT_APP_FIREBASE_APP_ID=1:123456789:web:abcdef123456
```

**Important**:
- The `REACT_APP_ADMIN_API_KEY` must match the `ADMIN_API_KEY` configured for the backend
- All Firebase configuration variables must be filled in from your Firebase Console
- The frontend automatically reads these from the root `.env` file

## Project Structure
```
frontend/
├── src/
│   ├── pages/                         # React page components
│   │   ├── LoginPage.js               # Authentication page with tenant registration
│   │   ├── DashboardPage.js           # Main dashboard with integration status
│   │   ├── AddIntegrationPage.js      # Add new integrations
│   │   ├── GmailIntegrationPage.js    # Gmail operations
│   │   ├── CalendarIntegrationPage.js # Calendar operations
│   │   ├── SendEmailPage.js           # Email composition
│   │   └── CreateEventPage.js         # Event creation
│   ├── context/                       # React context providers
│   │   └── AuthContext.js             # Authentication + tenant management
│   ├── services/                      # API and external services
│   │   └── api.js                     # Tenant-level API configuration
│   ├── components/                    # Reusable components
│   │   └── ChatbotWidget.js           # AI assistant widget
│   ├── styles/                        # CSS styles
│   ├── App.js                         # Main app component with routing
│   ├── firebase.js                    # Firebase configuration
│   └── index.js                       # App entry point
├── public/                            # Static assets
├── package.json                       # Dependencies and scripts
└── README.md                          # This file
```

## New Authentication & Tenant Flow

### User Onboarding Flow
1. **User** → LoginPage → Firebase Authentication (Google/GitHub/Email)
2. **AuthContext** → Automatically registers user as tenant using email username
3. **AuthContext** → Creates base configuration for tenant
4. **AuthContext** → Stores `plexus_user_auth_token` for MCP communication
5. **App** → Redirects to Dashboard → Tenant-level data loaded

### Integration Connection Flow
1. **User** → Dashboard → Clicks "Connect Gmail/Calendar"
2. **Dashboard** → Calls tenant-level OAuth endpoint (`/{entity_id}/gmail/login`)
3. **Backend** → OAuth flow → Tokens saved at tenant level
4. **Backend** → Automatically registers tools with tenant's MCP server
5. **Dashboard** → Updates integration status → Tools become available

### Data Persistence
- All OAuth tokens are stored at tenant level in backend database
- MCP tool registrations persist across server restarts
- Tenant configurations survive backend restarts
- Frontend automatically reconnects to existing tenant data

## API Integration

The frontend now communicates with tenant-level endpoints:

```javascript
// Tenant registration (automatic)
POST /admin/tenants/
POST /{entity_id}/plexus-auth/register-base-config

// Integration management
GET /{entity_id}/integrations
GET /{entity_id}/gmail/status
GET /{entity_id}/gmail/login
DELETE /{entity_id}/gmail/disconnect

// Similar patterns for Calendar and other integrations
```

## Visual Status Indicators

The dashboard displays clear integration status:
- 🟢 **Connected**: Integration is active with OAuth tokens stored
- 🔘 **Available**: Integration can be connected via OAuth flow
- 🔴 **Error**: Integration has issues (if implemented)

## Common vs Integration-Specific Tools

### Common Tools (Always Available)
- 🧮 Calculator - Perform mathematical calculations
- 📝 Text Processor - Process and manipulate text

### Gmail Tools (When Connected)
- 📧 Send Email - Compose and send emails
- 🔍 Search Emails - Search through your emails
- 📥 Read Latest Email - Get your most recent email

### Calendar Tools (When Connected)
- 📅 Create Event - Schedule new events
- 👁️ View Events - View your calendar events
- ✏️ Update Event - Modify existing events

## Setup Instructions

1. **Install dependencies**:
   ```bash
   cd frontend
   npm install
   ```
   This will automatically install `env-cmd` which allows the frontend to use the root `.env` file.

2. **Configure environment**:
   - Ensure root `.env` file is configured (copy from `env.example`)
   - Fill in all `REACT_APP_*` variables in the root `.env` file
   - Verify the admin API key matches between frontend and backend settings
   - Ensure backend URL points to port 8000

3. **Verify environment setup**:
   ```bash
   # From the frontend directory, check if variables are loaded
   npm run start
   # Check browser console for any environment variable errors
   # Verify in browser console: process.env.REACT_APP_BACKEND_URL
   ```

4. **Start development server**:
   ```bash
   npm start
   ```
   The `env-cmd` package will automatically load environment variables from the root `.env` file.

5. **Ensure backend is running**:
   - The `integrati_backend` must be running on port 8000
   - Admin API key must be configured in root `.env` file
   - Firebase service account must be configured

## Testing the Complete Flow

1. **User Registration**:
   - Sign up with new email → Tenant auto-created → Base config registered

2. **Gmail Integration**:
   - Click "Connect Gmail" → OAuth flow → Tokens stored → Tools registered → Dashboard updates

3. **Persistence Test**:
   - Restart backend → Login again → All integrations still connected → All tools available

4. **Tool Usage**:
   - Common tools work immediately
   - Gmail tools work after connection
   - AI assistant uses tenant-specific tools

## Troubleshooting

### Common Issues

1. **"Tenant not properly configured"**:
   - Check that `REACT_APP_ADMIN_API_KEY` matches `ADMIN_API_KEY` in root `.env`
   - Verify all required environment variables are set
   - Check browser console for registration errors

2. **OAuth flows not working**:
   - Verify backend is running on port 8000
   - Check that OAuth redirect URLs match backend configuration
   - Ensure plexus token is stored after registration

3. **Integration status not loading**:
   - Check that tenant ID is properly set
   - Verify plexus token exists in localStorage
   - Check network tab for API call errors

4. **Environment variables not loading**:
   - Ensure variables start with `REACT_APP_` prefix
   - Verify root `.env` file is in the correct location (project root)
   - Restart the development server after changing environment variables
   - If updating from previous version, run `npm install` to get the `env-cmd` dependency

5. **"env-cmd: command not found" or environment variables still not working**:
   - Run `npm install` in the frontend directory to install the `env-cmd` package
   - Verify the root `.env` file exists and contains `REACT_APP_*` variables
   - Check that the file path `../.env` is correct relative to the frontend directory
   - Try running `env-cmd -f ../.env echo $REACT_APP_BACKEND_URL` to test if env-cmd can read the file

### Debug Information

The application logs useful debug information to the browser console:
- Tenant registration process
- OAuth flow initiation
- Integration status loading
- Token storage and retrieval

Check the browser console for detailed error messages if issues occur.

## Architecture Highlights

### Tenant-Level Token Management
- One OAuth token per integration per tenant
- Tokens shared across all configurations within tenant
- Automatic token refresh handled by backend
- Persistent storage across system restarts

### MCP Integration
- Tools automatically registered when integrations connect
- Common tools always available
- Integration-specific tools appear when connected
- AI assistant has access to tenant-specific tool sets

### Progressive Enhancement
- Basic functionality works without integrations
- Additional tools unlock as integrations are connected
- Graceful degradation when services are unavailable
- Clear visual feedback for all states

### Unified Environment Configuration
- Single `.env` file for both frontend and backend
- Consistent variable naming and organization
- Simplified deployment and configuration management
- Clear separation between frontend and backend variables
