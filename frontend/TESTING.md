# Testing Guide - Tenant-Level Architecture Integration

This guide provides step-by-step instructions to test the complete user onboarding and integration flow with the new `integrati_backend` tenant-level architecture.

## Prerequisites

1. **Backend Running**: Ensure `integrati_backend` is running on port 8000
2. **Environment Setup**: Root `.env` file configured with all required variables:
   - `REACT_APP_BACKEND_URL=http://localhost:8000`
   - `REACT_APP_ADMIN_API_KEY=<matching ADMIN_API_KEY value>`
   - All `REACT_APP_FIREBASE_*` configuration variables
3. **Dependencies Installed**: Run `npm install` in the frontend directory to ensure `env-cmd` is installed
4. **Database Clean**: Start with a clean backend database for testing

**Important**:
- The frontend now uses the **root `.env` file** (not a separate frontend .env file)
- The `env-cmd` package is required to load environment variables from the root `.env` file
- Ensure all `REACT_APP_*` variables are configured in the root `.env` file

## Test Scenarios

### 1. User Registration & Tenant Creation

**Test Steps:**
1. Navigate to `http://localhost:3000`
2. Click "Sign Up" or use Google/GitHub authentication
3. Create account with email: `testuser@example.com`

**Expected Results:**
- ✅ User successfully authenticated
- ✅ Console logs show: "Ensuring tenant registration for: testuser, testuser@example.com"
- ✅ Console logs show: "Tenant registered successfully: testuser"
- ✅ Console logs show: "Base config registered"
- ✅ Console logs show: "Plexus token stored for tenant: testuser"
- ✅ Redirected to dashboard showing tenant info

**Verification:**
```bash
# Check localStorage in browser console
localStorage.getItem('jwt_token')           // Should exist
localStorage.getItem('plexus_user_auth_token') // Should exist
localStorage.getItem('tenant_id')           // Should be 'testuser'
localStorage.getItem('user_email')          // Should be 'testuser@example.com'
```

### 2. Dashboard Integration Display

**Test Steps:**
1. After successful login, observe dashboard content

**Expected Results:**
- ✅ Dashboard shows: "Tenant: testuser • Manage your integrations and services"
- ✅ Common Tools section displays:
  - 🧮 Calculator
  - 📝 Text Processor
- ✅ Integrations section shows:
  - Gmail card with "🔘 Available" status and "Connect" button
  - Calendar card with "🔘 Available" status and "Connect" button
- ✅ No integration-specific tools visible yet

### 3. Gmail OAuth Connection Flow

**Test Steps:**
1. Click "Connect" button on Gmail integration card
2. Complete OAuth flow (may redirect to Google)
3. Return to dashboard after OAuth completion

**Expected Results:**
- ✅ Console logs show: "Starting gmail OAuth flow for tenant: testuser"
- ✅ Browser redirects to Google OAuth consent screen
- ✅ After consent, backend processes OAuth callback
- ✅ Dashboard updates automatically showing:
  - Gmail card with "🟢 Connected" status and "Disconnect" button
  - Gmail tools now visible:
    - 📧 Send Email
    - 🔍 Search Emails
    - 📥 Read Latest Email

**Verification:**
- Click on Gmail card to navigate to Gmail integration page
- Should show "🟢 Connected" status
- Gmail features should be accessible

### 4. Integration Persistence Test

**Test Steps:**
1. After connecting Gmail, restart the `integrati_backend` server
2. Keep frontend running and refresh the page
3. Login again with the same credentials

**Expected Results:**
- ✅ User automatically logs in (existing localStorage tokens)
- ✅ Dashboard shows Gmail still connected (🟢 Connected)
- ✅ Gmail tools still visible and accessible
- ✅ No need to re-authenticate Gmail

**Verification:**
```bash
# Backend should show OAuth tokens persisted across restart
# Check backend logs for successful token retrieval
```

### 5. Multiple Integration Testing

**Test Steps:**
1. With Gmail connected, now connect Calendar integration
2. Click "Connect" on Calendar card
3. Complete Calendar OAuth flow

**Expected Results:**
- ✅ Both Gmail and Calendar show "🟢 Connected"
- ✅ Calendar tools become visible:
  - 📅 Create Event
  - 👁️ View Events
  - ✏️ Update Event
- ✅ Gmail integration remains connected
- ✅ All tools accessible to AI assistant (MCP integration)

### 6. Tool Usage Testing

**Test Steps:**
1. Click on Gmail tools (Send Email, Search Emails)
2. Click on Calendar tools
3. Try using ChatbotWidget with connected integrations

**Expected Results:**
- ✅ Tool pages load correctly
- ✅ Pages show tenant information and connection status
- ✅ Gmail integration page shows connected status
- ✅ Email functions work (if backend implements them)
- ✅ ChatbotWidget has access to tenant-specific tools

### 7. Error Handling & Edge Cases

**Test Steps:**
1. Try accessing Gmail page when not connected
2. Test with invalid/expired tokens
3. Test network connection issues

**Expected Results:**
- ✅ Proper error messages displayed
- ✅ Connection prompts when integration not available
- ✅ Graceful fallback behavior
- ✅ Clear user feedback for all states

### 8. Multi-User Tenant Isolation

**Test Steps:**
1. Login with first user: `user1@example.com`
2. Connect Gmail integration
3. Logout and login with second user: `user2@example.com`
4. Check integration status

**Expected Results:**
- ✅ `user2` starts with no connected integrations
- ✅ `user2` has separate tenant ID (`user1` vs `user2`)
- ✅ Each user's integrations are isolated
- ✅ OAuth tokens not shared between different tenants

## Debug Information

### Browser Console Logs

During testing, monitor browser console for these key logs:

```javascript
// Tenant Registration
"Ensuring tenant registration for: testuser, testuser@example.com"
"Tenant registered successfully: testuser"
"Base config registered: {plexus_user_auth_token: '...'}"
"Plexus token stored for tenant: testuser"

// Integration Status Loading
"Loading integration status for tenant: testuser"
"Gmail status: {connected: true, ...}"
"Calendar status: {connected: false, ...}"

// OAuth Flow
"Starting gmail OAuth flow for tenant: testuser"
"Starting calendar OAuth flow for tenant: testuser"
```

### Backend Verification

Check backend logs for:

```bash
# Tenant Registration
POST /admin/tenants/ - 201 Created
POST /testuser/plexus-auth/register-base-config - 200 OK

# OAuth Flow
GET /testuser/gmail/login - 302 Redirect
GET /testuser/gmail/callback - 200 OK (after OAuth)

# Status Checks
GET /testuser/gmail/status - 200 OK
GET /testuser/calendar/status - 200 OK
```

### Database Verification

If you have access to the backend database:

```sql
-- Check tenant creation
SELECT * FROM tenants WHERE entity_id = 'testuser';

-- Check OAuth tokens persistence
SELECT * FROM oauth_tokens WHERE tenant_id = 'testuser';

-- Check MCP tool registrations
SELECT * FROM mcp_tools WHERE tenant_id = 'testuser';
```

## Common Issues & Troubleshooting

### "Tenant not properly configured"
- **Cause**: Admin API key mismatch or missing environment variables
- **Fix**: Verify `REACT_APP_ADMIN_API_KEY` matches `ADMIN_API_KEY` in root `.env` file

### OAuth flows not working
- **Cause**: Backend not running or wrong URL configuration
- **Fix**: Ensure backend is on port 8000, check `REACT_APP_BACKEND_URL` in root `.env`

### Integration status not loading
- **Cause**: Missing plexus token or tenant ID
- **Fix**: Check localStorage values, verify environment variables, re-login if needed

### Tools not appearing after connection
- **Cause**: Backend MCP registration failed
- **Fix**: Check backend logs for MCP server errors

### Environment variables not loading
- **Cause**: Variables not properly configured in root `.env` file
- **Fix**:
  - Ensure all `REACT_APP_*` variables are in the **root** `.env` file (not frontend/.env)
  - Verify variables start with `REACT_APP_` prefix
  - Restart development server after changing environment variables
  - Check that root `.env` file exists and is properly formatted

### Firebase authentication issues
- **Cause**: Missing or incorrect Firebase configuration
- **Fix**: Verify all `REACT_APP_FIREBASE_*` variables are correctly set in root `.env` file

## Environment Setup Verification

Before running tests, verify your root `.env` file contains:

```bash
# Required Frontend Variables (in root .env file)
REACT_APP_BACKEND_URL=http://localhost:8000
REACT_APP_ADMIN_API_KEY=your-admin-api-key-change-this-in-production
REACT_APP_DEBUG=true

# Required Firebase Variables
REACT_APP_FIREBASE_API_KEY=your-firebase-api-key
REACT_APP_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
REACT_APP_FIREBASE_PROJECT_ID=your-firebase-project-id
REACT_APP_FIREBASE_STORAGE_BUCKET=your-project.appspot.com
REACT_APP_FIREBASE_MESSAGING_SENDER_ID=123456789
REACT_APP_FIREBASE_APP_ID=1:123456789:web:abcdef123456

# Backend API Key (must match REACT_APP_ADMIN_API_KEY)
ADMIN_API_KEY=your-admin-api-key-change-this-in-production
```

## Success Criteria Checklist

Complete end-to-end flow verification:

- [ ] Root `.env` file properly configured with all `REACT_APP_*` variables
- [ ] New user automatically becomes tenant
- [ ] Base configuration created with plexus token
- [ ] Dashboard shows proper integration status
- [ ] OAuth flows connect integrations successfully
- [ ] Integration tools appear after connection
- [ ] Data persists across backend restarts
- [ ] Multiple users have isolated tenants
- [ ] Error handling works gracefully
- [ ] MCP tools available to AI assistant
- [ ] All localStorage tokens managed correctly
- [ ] Environment variables properly loaded from root `.env` file

## Performance Notes

Expected performance characteristics:

- **Login**: < 3 seconds including tenant registration
- **OAuth Flow**: < 10 seconds end-to-end
- **Dashboard Load**: < 2 seconds with integration status
- **Tool Registration**: Automatic, no user delay
- **Persistence**: Immediate availability after restart

All tests should complete successfully for the integration to be considered functional.
