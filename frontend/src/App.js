import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import AddIntegrationPage from './pages/AddIntegrationPage';
import GmailIntegrationPage from './pages/GmailIntegrationPage';
import CalendarIntegrationPage from './pages/CalendarIntegrationPage';
import SendEmailPage from './pages/SendEmailPage';
import CreateEventPage from './pages/CreateEventPage';
import { AuthProvider, useAuth } from './context/AuthContext';

const PrivateRoute = ({ children }) => {
    const { user, token, loading } = useAuth();
    
    if (loading) {
        return <div>Loading...</div>;
    }
    
    // Check for either Firebase user or JWT token
    if (user || token) {
        return children;
    } else {
        return <Navigate to="/login" />;
    }
};

function App() {
    return (
        <Router>
            <AuthProvider>
                <Routes>
                    <Route path="/login" element={<LoginPage />} />
                    <Route
                        path="/dashboard"
                        element={
                            <PrivateRoute>
                                <DashboardPage />
                            </PrivateRoute>
                        }
                    />
                    <Route
                        path="/add-integration"
                        element={
                            <PrivateRoute>
                                <AddIntegrationPage />
                            </PrivateRoute>
                        }
                    />
                    <Route
                        path="/integration/gmail/:integrationId"
                        element={
                            <PrivateRoute>
                                <GmailIntegrationPage />
                            </PrivateRoute>
                        }
                    />
                    <Route
                        path="/integration/calendar/:integrationId"
                        element={
                            <PrivateRoute>
                                <CalendarIntegrationPage />
                            </PrivateRoute>
                        }
                    />
                    <Route
                        path="/send-email"
                        element={
                            <PrivateRoute>
                                <SendEmailPage />
                            </PrivateRoute>
                        }
                    />
                    <Route
                        path="/create-event"
                        element={
                            <PrivateRoute>
                                <CreateEventPage />
                            </PrivateRoute>
                        }
                    />
                    <Route path="/" element={<Navigate to="/login" replace />} />
                    <Route path="*" element={<Navigate to="/login" replace />} />
                </Routes>
            </AuthProvider>
        </Router>
    );
}

export default App; 