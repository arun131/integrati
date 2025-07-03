# Gmail Manager Frontend

This is the React frontend for the Gmail & Calendar Manager MVP.

## Setup

1. Install dependencies:
   ```bash
   npm install
   npm install jwt-decode
   ```
2. Create a `.env.development` file with:
   ```
   REACT_APP_BACKEND_URL=http://localhost:8000
   ```
3. Start the development server:
   ```bash
   npm start
   ```

## Deployment

- Set `REACT_APP_BACKEND_URL` in `.env.production` to your deployed backend URL.
- Deploy to Vercel or your preferred platform. 