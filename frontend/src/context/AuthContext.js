import React, { createContext, useState, useContext, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
    const [token, setToken] = useState(localStorage.getItem('jwt_token'));
    const [userEmail, setUserEmail] = useState(localStorage.getItem('user_email'));
    const navigate = useNavigate();

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

    const login = (jwtToken, email) => {
        setToken(jwtToken);
        setUserEmail(email);
        navigate('/dashboard');
    };

    const logout = () => {
        setToken(null);
        setUserEmail(null);
        navigate('/login');
    };

    return (
        <AuthContext.Provider value={{ token, userEmail, login, logout }}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => useContext(AuthContext); 