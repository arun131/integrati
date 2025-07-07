import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate, useLocation } from 'react-router-dom';
import { jwtDecode } from 'jwt-decode';
import { initializeApp } from 'firebase/app';
import { getFirestore, collection, doc, setDoc } from 'firebase/firestore';
import { getAuth } from 'firebase/auth';

function LoginPage() {
    const { signInWithGoogle, signInWithGithub, signInWithEmail, signUpWithEmail, login } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [isSignUp, setIsSignUp] = useState(false);
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        const handleToken = async () => {
            const queryParams = new URLSearchParams(location.search);
            const token = queryParams.get('token');
            if (token) {
                try {
                    const decoded = jwtDecode(token);
                    const userEmail = decoded.sub || decoded.email || '';
                    
                    // First, login the user
                    await login(token, userEmail);
                    
                    // Then handle the integration if present
                    const integrationType = queryParams.get('integration');
                    if (integrationType) {
                        try {
                            // Initialize Firebase if not already initialized
                            let app;
                            try {
                                app = window.firebase.app();
                            } catch (e) {
                                const firebaseConfig = {
                                    apiKey: process.env.REACT_APP_FIREBASE_API_KEY,
                                    authDomain: process.env.REACT_APP_FIREBASE_AUTH_DOMAIN,
                                    projectId: process.env.REACT_APP_FIREBASE_PROJECT_ID,
                                    storageBucket: process.env.REACT_APP_FIREBASE_STORAGE_BUCKET,
                                    messagingSenderId: process.env.REACT_APP_FIREBASE_MESSAGING_SENDER_ID,
                                    appId: process.env.REACT_APP_FIREBASE_APP_ID
                                };
                                app = initializeApp(firebaseConfig);
                            }
                            const db = getFirestore(app);
                            const auth = getAuth(app);
                            await new Promise((resolve) => {
                                const unsubscribe = auth.onAuthStateChanged((user) => {
                                    unsubscribe();
                                    resolve(user);
                                });
                            });
                            const currentUser = auth.currentUser;
                            if (currentUser) {
                                const integrationData = {
                                    userId: currentUser.uid,
                                    type: integrationType,
                                    status: 'active',
                                    createdAt: new Date().toISOString(),
                                    debug_timestamp: Date.now()
                                };
                                const docRef = doc(collection(db, 'integrations'));
                                await setDoc(docRef, integrationData);
                                navigate('/dashboard', { replace: true });
                            }
                        } catch (e) {
                            // Swallow error or set error state if needed
                        }
                    }
                } catch (err) {
                    setError('Invalid token received from backend.');
                }
            }
        };
        
        handleToken();
    }, [location, login, navigate]);

    const handleGoogleSignIn = async () => {
        setLoading(true);
        setError('');
        try {
            await signInWithGoogle();
            navigate('/dashboard');
        } catch (error) {
            setError('Failed to sign in with Google: ' + error.message);
        } finally {
            setLoading(false);
        }
    };

    const handleGithubSignIn = async () => {
        setLoading(true);
        setError('');
        try {
            await signInWithGithub();
            navigate('/dashboard');
        } catch (error) {
            setError('Failed to sign in with GitHub: ' + error.message);
        } finally {
            setLoading(false);
        }
    };

    const handleEmailAuth = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError('');
        
        try {
            if (isSignUp) {
                await signUpWithEmail(email, password);
            } else {
                await signInWithEmail(email, password);
            }
            navigate('/dashboard');
        } catch (error) {
            setError(error.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={{ 
            display: 'flex', 
            justifyContent: 'center', 
            alignItems: 'center', 
            minHeight: '100vh',
            backgroundColor: '#f5f5f5',
            fontFamily: 'Arial, sans-serif'
        }}>
            <div style={{
                backgroundColor: 'white',
                padding: '40px',
                borderRadius: '10px',
                boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
                width: '100%',
                maxWidth: '400px'
            }}>
                <h2 style={{ textAlign: 'center', marginBottom: '30px', color: '#333' }}>
                    Welcome to Integrati
                </h2>
                <p style={{ textAlign: 'center', marginBottom: '30px', color: '#666' }}>
                    Connect your favorite services and manage them all in one place
                </p>

                {error && (
                    <div style={{
                        backgroundColor: '#ffebee',
                        color: '#c62828',
                        padding: '10px',
                        borderRadius: '5px',
                        marginBottom: '20px',
                        fontSize: '14px'
                    }}>
                        {error}
                    </div>
                )}

                <form onSubmit={handleEmailAuth} style={{ marginBottom: '20px' }}>
                    <input
                        type="email"
                        placeholder="Email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        autoComplete="email"
                        style={{
                            width: '100%',
                            padding: '12px',
                            marginBottom: '10px',
                            border: '1px solid #ddd',
                            borderRadius: '5px',
                            fontSize: '16px'
                        }}
                        required
                    />
                    <input
                        type="password"
                        placeholder="Password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        autoComplete="current-password"
                        style={{
                            width: '100%',
                            padding: '12px',
                            marginBottom: '15px',
                            border: '1px solid #ddd',
                            borderRadius: '5px',
                            fontSize: '16px'
                        }}
                        required
                    />
                    <button
                        type="submit"
                        disabled={loading}
                        style={{
                            width: '100%',
                            padding: '12px',
                            backgroundColor: '#4285f4',
                            color: 'white',
                            border: 'none',
                            borderRadius: '5px',
                            fontSize: '16px',
                            cursor: loading ? 'not-allowed' : 'pointer',
                            opacity: loading ? 0.7 : 1
                        }}
                    >
                        {loading ? 'Loading...' : (isSignUp ? 'Sign Up' : 'Sign In')}
                    </button>
                </form>

                <div style={{ textAlign: 'center', marginBottom: '20px' }}>
                    <button
                        onClick={() => setIsSignUp(!isSignUp)}
                        style={{
                            background: 'none',
                            border: 'none',
                            color: '#4285f4',
                            cursor: 'pointer',
                            textDecoration: 'underline'
                        }}
                    >
                        {isSignUp ? 'Already have an account? Sign In' : "Don't have an account? Sign Up"}
                    </button>
                </div>

                <div style={{ textAlign: 'center', marginBottom: '20px' }}>
                    <span style={{ color: '#666' }}>or</span>
                </div>

                <button
                    onClick={handleGoogleSignIn}
                    disabled={loading}
                    style={{
                        width: '100%',
                        padding: '12px',
                        marginBottom: '10px',
                        backgroundColor: '#db4437',
                        color: 'white',
                        border: 'none',
                        borderRadius: '5px',
                        fontSize: '16px',
                        cursor: loading ? 'not-allowed' : 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        opacity: loading ? 0.7 : 1
                    }}
                >
                    <img
                        src="https://img.icons8.com/color/48/000000/google-logo.png"
                        alt="Google"
                        style={{ width: '20px', height: '20px', marginRight: '10px' }}
                    />
                    Continue with Google
                </button>

                <button
                    onClick={handleGithubSignIn}
                    disabled={loading}
                    style={{
                        width: '100%',
                        padding: '12px',
                        backgroundColor: '#333',
                        color: 'white',
                        border: 'none',
                        borderRadius: '5px',
                        fontSize: '16px',
                        cursor: loading ? 'not-allowed' : 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        opacity: loading ? 0.7 : 1
                    }}
                >
                    <svg
                        width="20"
                        height="20"
                        viewBox="0 0 24 24"
                        fill="currentColor"
                        style={{ marginRight: '10px' }}
                    >
                        <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
                    </svg>
                    Continue with GitHub
                </button>
            </div>
        </div>
    );
}

export default LoginPage; 