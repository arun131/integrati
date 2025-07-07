const { initializeApp } = require('firebase/app');

const firebaseConfig = {
  apiKey: process.env.REACT_APP_FIREBASE_API_KEY || 'YOUR_API_KEY',
  authDomain: process.env.REACT_APP_FIREBASE_AUTH_DOMAIN || 'YOUR_AUTH_DOMAIN',
  projectId: process.env.REACT_APP_FIREBASE_PROJECT_ID || 'YOUR_PROJECT_ID',
  storageBucket: process.env.REACT_APP_FIREBASE_STORAGE_BUCKET || 'YOUR_STORAGE_BUCKET',
  messagingSenderId: process.env.REACT_APP_FIREBASE_MESSAGING_SENDER_ID || 'YOUR_MESSAGING_SENDER_ID',
  appId: process.env.REACT_APP_FIREBASE_APP_ID || 'YOUR_APP_ID'
};

try {
  const app = initializeApp(firebaseConfig);
  console.log('Firebase initialized:', app.name);
} catch (e) {
  console.error('Firebase init error:', e);
} 