import React, { createContext, useState, useContext, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  signInWithPopup,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signOut,
  onAuthStateChanged
} from 'firebase/auth';
import { auth, googleProvider, githubProvider } from '../firebase';
import { tenantApi } from '../services/api';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
    const [token, setToken] = useState(localStorage.getItem('jwt_token'));
    const [plexusToken, setPlexusToken] = useState(localStorage.getItem('plexus_user_auth_token'));
    const [userEmail, setUserEmail] = useState(localStorage.getItem('user_email'));
    const [tenantId, setTenantId] = useState(localStorage.getItem('tenant_id'));
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const navigate = useNavigate();
    // Add a new state for tenant registration errors
    const [tenantRegistrationError, setTenantRegistrationError] = useState('');

    useEffect(() => {
        const unsubscribe = onAuthStateChanged(auth, async (user) => {
            setUser(user);

            // If we have a Firebase user, proceed directly to tenant registration
            if (user && !plexusToken) {
                try {
                    setUserEmail(user.email);

                    // Proceed directly to tenant registration without JWT token
                    await exchangeFirebaseToken(user.getIdToken());
                } catch (error) {
                    console.error('Error during tenant registration:', error);
                }
            } else if (!user) {
                // User signed out, clear all tokens and data
                setToken(null);
                setUserEmail(null);
                setPlexusToken(null);
                setTenantId(null);
            }
        });

        // Always set loading to false after first auth check
        setLoading(false);

        return () => unsubscribe();
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [plexusToken]);

    useEffect(() => {
        // Store all tokens and identifiers in localStorage
        if (token) {
            localStorage.setItem('jwt_token', token);
        } else {
            localStorage.removeItem('jwt_token');
        }

        if (plexusToken) {
            localStorage.setItem('plexus_user_auth_token', plexusToken);
        } else {
            localStorage.removeItem('plexus_user_auth_token');
        }

        if (userEmail) {
            localStorage.setItem('user_email', userEmail);
        } else {
            localStorage.removeItem('user_email');
        }

        if (tenantId) {
            localStorage.setItem('tenant_id', tenantId);
        } else {
            localStorage.removeItem('tenant_id');
        }
    }, [token, plexusToken, userEmail, tenantId]);

    // Add a new function to exchange Firebase ID token for Plexus token and tenant info
    const exchangeFirebaseToken = async (idToken) => {
        try {
            setTenantRegistrationError('');

            // Validate idToken - be more strict about validation
            if (!idToken || typeof idToken !== 'string' || idToken.trim() === '') {
                console.error('Invalid idToken:', idToken);
                setTenantRegistrationError('Invalid Firebase token');
                return null;
            }

            // Additional validation to ensure it's a proper JWT token
            if (!idToken.includes('.') || idToken.split('.').length !== 3) {
                console.error('Invalid JWT format:', idToken);
                setTenantRegistrationError('Invalid Firebase token format');
                return null;
            }

            console.log('Exchanging Firebase token, length:', idToken.length);
            const response = await fetch(`${process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000'}/auth/firebase-token`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ id_token: idToken }),
            });

            console.log('Response status:', response.status);

            if (!response.ok) {
                let errorData;
                try {
                    errorData = await response.json();
                } catch (e) {
                    errorData = { detail: response.statusText };
                }
                console.error('Firebase token exchange failed:', errorData);
                setTenantRegistrationError('Failed to exchange Firebase token: ' + (typeof errorData.detail === 'object' ? JSON.stringify(errorData.detail) : errorData.detail || response.statusText));
                return null;
            }

            const data = await response.json();
            console.log('Firebase token exchange successful:', data);
            setPlexusToken(data.plexus_token);
            setTenantId(data.entity_id);
            setUserEmail(data.email);
            return data;
        } catch (error) {
            console.error('Error exchanging Firebase token:', error);
            setTenantRegistrationError('Error exchanging Firebase token: ' + (typeof error === 'object' ? JSON.stringify(error) : error));
            return null;
        }
    };

    const signInWithGoogle = async () => {
        try {
            console.log('Starting Google sign in...');
            const result = await signInWithPopup(auth, googleProvider);
            console.log('Google sign in successful, getting ID token...');
            const idToken = await result.user.getIdToken();
            console.log('ID token retrieved, length:', idToken ? idToken.length : 'null');
            await exchangeFirebaseToken(idToken);
            return result.user;
        } catch (error) {
            console.error('Error in Google sign in:', error);
            throw error;
        }
    };

    const signInWithGithub = async () => {
        try {
            console.log('Starting Github sign in...');
            const result = await signInWithPopup(auth, githubProvider);
            console.log('Github sign in successful, getting ID token...');
            const idToken = await result.user.getIdToken();
            console.log('ID token retrieved, length:', idToken ? idToken.length : 'null');
            await exchangeFirebaseToken(idToken);
            return result.user;
        } catch (error) {
            console.error('Error in Github sign in:', error);
            throw error;
        }
    };

    const signInWithEmail = async (email, password) => {
        try {
            console.log('Starting email sign in...');
            const result = await signInWithEmailAndPassword(auth, email, password);
            console.log('Email sign in successful, getting ID token...');
            const idToken = await result.user.getIdToken();
            console.log('ID token retrieved, length:', idToken ? idToken.length : 'null');
            await exchangeFirebaseToken(idToken);
            return result.user;
        } catch (error) {
            console.error('Error in email sign in:', error);
            throw error;
        }
    };

    const signUpWithEmail = async (email, password) => {
        try {
            const result = await createUserWithEmailAndPassword(auth, email, password);
            return result.user;
        } catch (error) {
            throw error;
        }
    };

    const login = async (email, skipTenantRegistration = false) => {
        setUserEmail(email);
        navigate('/dashboard');
    };

    const logout = async () => {
        try {
            // Sign out from Firebase
            await signOut(auth);
        } catch (error) {
            console.error('Error signing out from Firebase:', error);
        }

        // Clear all tokens and data
        setToken(null);
        setPlexusToken(null);
        setUserEmail(null);
        setTenantId(null);
        setUser(null);
        navigate('/login');
    };

    const value = {
        token,
        plexusToken,
        userEmail,
        tenantId,
        user,
        loading,
        setToken,
        setPlexusToken,
        setUserEmail,
        setTenantId,
        login,
        logout,
        signInWithGoogle,
        signInWithGithub,
        signInWithEmail,
        signUpWithEmail,
        tenantRegistrationError, // <-- keep this
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
