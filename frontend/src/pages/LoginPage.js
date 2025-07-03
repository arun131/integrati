import React, { useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { jwtDecode } from 'jwt-decode';

function LoginPage() {
    const { login } = useAuth();
    const location = useLocation();

    useEffect(() => {
        const queryParams = new URLSearchParams(location.search);
        const token = queryParams.get('token');
        console.log("Token from URL:", token);
        if (token) {
            try {
                const decoded = jwtDecode(token);
                const userEmail = decoded.sub;
                console.log("Decoded JWT:", decoded);
                login(token, userEmail);
            } catch (error) {
                console.error("Failed to decode JWT token:", error);
            }
        } else {
            console.log("No token found in URL.");
        }
    }, [location, login]);

    const handleGoogleLogin = () => {
        window.location.href = `${process.env.REACT_APP_BACKEND_URL}/auth/google/login`;
    };

    return (
        <div style={{ textAlign: 'center', marginTop: '50px' }}>
            <h2>Welcome to Gmail Manager</h2>
            <p>Please log in with your Gmail account to continue.</p>
            <button
                onClick={handleGoogleLogin}
                style={{
                    padding: '10px 20px',
                    fontSize: '16px',
                    cursor: 'pointer',
                    backgroundColor: '#4285F4',
                    color: 'white',
                    border: 'none',
                    borderRadius: '5px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    margin: '20px auto',
                    boxShadow: '0 2px 4px rgba(0,0,0,0.2)'
                }}
            >
                <img
                    src="https://img.icons8.com/color/48/000000/google-logo.png"
                    alt="Google logo"
                    style={{ width: '24px', height: '24px', marginRight: '10px' }}
                />
                Sign in with Google
            </button>
        </div>
    );
}

export default LoginPage; 