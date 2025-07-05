import React, { createContext, useState, useContext, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  signInWithPopup, 
  signInWithEmailAndPassword, 
  createUserWithEmailAndPassword,
  signOut,
  onAuthStateChanged,
  GoogleAuthProvider,
  GithubAuthProvider
} from 'firebase/auth';
import { auth, googleProvider, githubProvider } from '../firebase';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
    const [token, setToken] = useState(localStorage.getItem('jwt_token'));
    const [userEmail, setUserEmail] = useState(localStorage.getItem('user_email'));
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const navigate = useNavigate();

    useEffect(() => {
        const unsubscribe = onAuthStateChanged(auth, async (user) => {
            setUser(user);
            
            // If we have a Firebase user but no JWT token, get one from backend
            if (user && !token) {
                try {
                    const idToken = await user.getIdToken();
                    const response = await fetch(
                        `${process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000'}/api/auth/firebase-token`,
                        {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ id_token: idToken }),
                        }
                    );
                    if (response.ok) {
                        const data = await response.json();
                        setToken(data.access_token);
                        setUserEmail(user.email);
                    } else {
                        console.error('Failed to get backend JWT for Firebase user');
                    }
                } catch (error) {
                    console.error('Error getting backend JWT:', error);
                }
            }
            
            // Only set loading to false if we have either a user or a token
            if (user || token) {
                setLoading(false);
            }
        });

        // If we have a JWT token but no Firebase user, still consider authenticated
        if (token && !user) {
            setLoading(false);
        }

        return () => unsubscribe();
    }, [token]);

    useEffect(() => {
        if (token) {
            localStorage.setItem('jwt_token', token);
        } else {
            localStorage.removeItem('jwt_token');
        }
        if (userEmail) {
            localStorage.setItem('user_email', userEmail);
        } else {
            localStorage.removeItem('user_email');
        }
    }, [token, userEmail]);

    const signInWithGoogle = async () => {
        try {
            const result = await signInWithPopup(auth, googleProvider);
            return result.user;
        } catch (error) {
            console.error('Google sign-in error:', error);
            throw error;
        }
    };

    const signInWithGithub = async () => {
        try {
            const result = await signInWithPopup(auth, githubProvider);
            return result.user;
        } catch (error) {
            console.error('GitHub sign-in error:', error);
            throw error;
        }
    };

    const signInWithEmail = async (email, password) => {
        try {
            const result = await signInWithEmailAndPassword(auth, email, password);
            return result.user;
        } catch (error) {
            console.error('Email sign-in error:', error);
            throw error;
        }
    };

    const signUpWithEmail = async (email, password) => {
        try {
            const result = await createUserWithEmailAndPassword(auth, email, password);
            return result.user;
        } catch (error) {
            console.error('Email sign-up error:', error);
            throw error;
        }
    };

    const login = (jwtToken, email) => {
        setToken(jwtToken);
        setUserEmail(email);
        navigate('/dashboard');
    };

    const logout = async () => {
        try {
            // Sign out from Firebase
            await signOut(auth);
        } catch (error) {
            console.error('Firebase logout error:', error);
        }
        
        // Clear JWT token and email
        setToken(null);
        setUserEmail(null);
        setUser(null);
        navigate('/login');
    };

    const value = {
        token,
        userEmail,
        user,
        loading,
        signInWithGoogle,
        signInWithGithub,
        signInWithEmail,
        signUpWithEmail,
        login,
        logout
    };

    return (
        <AuthContext.Provider value={value}>
            {!loading && children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
}; 