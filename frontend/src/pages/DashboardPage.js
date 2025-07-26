import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import ChatbotWidget from '../components/ChatbotWidget';

function DashboardPage() {
    const { user, logout } = useAuth();
    const navigate = useNavigate();
    const [integrations, setIntegrations] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (user) {
            loadUserIntegrations();
        } else {
            setLoading(false);
        }
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [user]);

    const loadUserIntegrations = async () => {
        try {
            // Add a longer delay to ensure backend has processed integration creation
            await new Promise(resolve => setTimeout(resolve, 1000));

            // Debug: Check if we have a token
            const token = localStorage.getItem('jwt_token');
            console.log('Dashboard: JWT token exists:', !!token);
            console.log('Dashboard: User object:', user);

            const response = await api.get('/api/integration/integrations');
            console.log('Dashboard: Integrations loaded:', response.data);
            setIntegrations(response.data);
        } catch (error) {
            console.error('Error loading integrations:', error);
            console.error('Error response:', error.response?.data);

            // If we get 401, try again after a longer delay (for OAuth redirects)
            if (error.response?.status === 401) {
                console.log('Got 401, retrying after longer delay...');
                await new Promise(resolve => setTimeout(resolve, 2000));
                try {
                    const retryResponse = await api.get('/api/integration/integrations');
                    console.log('Dashboard: Integrations loaded on retry:', retryResponse.data);
                    setIntegrations(retryResponse.data);
                } catch (retryError) {
                    console.error('Retry also failed:', retryError);
                }
            }
        } finally {
            setLoading(false);
        }
    };

    const handleAddIntegration = () => {
        navigate('/add-integration');
    };

    const handleIntegrationClick = (integration) => {
        if (integration.status === 'pending') {
            alert(`${getIntegrationName(integration.integration_name)} integration is pending. OAuth setup will be implemented soon!`);
        } else {
            // Map integration names to the correct routes
            const routeMap = {
                'gmail': '/integration/gmail',
                'calendar': '/integration/calendar'
            };

            const baseRoute = routeMap[integration.integration_name];
            if (baseRoute) {
                navigate(`${baseRoute}/${integration.id}`);
            } else {
                console.error('Unknown integration type:', integration.integration_name);
            }
        }
    };

    const handleLogout = () => {
        logout();
    };

    if (loading) {
        return (
            <div style={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                height: '100vh'
            }}>
                <div>Loading...</div>
            </div>
        );
    }

    const token = localStorage.getItem('jwt_token');

    return (
        <div style={{
            padding: '20px',
            maxWidth: '1200px',
            margin: 'auto',
            fontFamily: 'Arial, sans-serif'
        }}>
            <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '30px',
                borderBottom: '1px solid #eee',
                paddingBottom: '20px'
            }}>
                <div>
                    <h1 style={{ color: '#333', margin: '0 0 5px 0' }}>
                        Welcome, {user?.displayName || user?.email}!
                    </h1>
                    <p style={{ color: '#666', margin: '0' }}>
                        Manage your integrations and services
                    </p>
                </div>
                <button
                    onClick={handleLogout}
                    style={{
                        padding: '10px 20px',
                        backgroundColor: '#dc3545',
                        color: 'white',
                        border: 'none',
                        borderRadius: '5px',
                        cursor: 'pointer',
                        fontSize: '14px'
                    }}
                >
                    Logout
                </button>
            </div>

            <div style={{ marginBottom: '30px' }}>
                <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: '20px'
                }}>
                    <h2 style={{ color: '#333', margin: '0' }}>Your Integrations</h2>
                    <button
                        onClick={handleAddIntegration}
                        style={{
                            padding: '12px 24px',
                            backgroundColor: '#28a745',
                            color: 'white',
                            border: 'none',
                            borderRadius: '5px',
                            cursor: 'pointer',
                            fontSize: '16px',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px'
                        }}
                    >
                        <span>+</span>
                        Add Integration
                    </button>
                </div>

                {integrations.length === 0 ? (
                    <div style={{
                        textAlign: 'center',
                        padding: '40px',
                        backgroundColor: '#f8f9fa',
                        borderRadius: '10px',
                        border: '2px dashed #dee2e6'
                    }}>
                        <h3 style={{ color: '#6c757d', marginBottom: '10px' }}>
                            No integrations yet
                        </h3>
                        <p style={{ color: '#6c757d', marginBottom: '20px' }}>
                            Get started by adding your first integration
                        </p>
                        <button
                            onClick={handleAddIntegration}
                            style={{
                                padding: '10px 20px',
                                backgroundColor: '#007bff',
                                color: 'white',
                                border: 'none',
                                borderRadius: '5px',
                                cursor: 'pointer'
                            }}
                        >
                            Add Your First Integration
                        </button>
                    </div>
                ) : (
                    <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
                        gap: '20px'
                    }}>
                        {integrations.map((integration) => (
                            <div
                                key={integration.id}
                                onClick={() => handleIntegrationClick(integration)}
                                style={{
                                    backgroundColor: 'white',
                                    border: '1px solid #dee2e6',
                                    borderRadius: '10px',
                                    padding: '20px',
                                    cursor: 'pointer',
                                    transition: 'all 0.2s ease',
                                    boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
                                }}
                                onMouseEnter={(e) => {
                                    e.target.style.transform = 'translateY(-2px)';
                                    e.target.style.boxShadow = '0 4px 8px rgba(0,0,0,0.15)';
                                }}
                                onMouseLeave={(e) => {
                                    e.target.style.transform = 'translateY(0)';
                                    e.target.style.boxShadow = '0 2px 4px rgba(0,0,0,0.1)';
                                }}
                            >
                                <div style={{ display: 'flex', alignItems: 'center', marginBottom: '15px' }}>
                                    <div style={{
                                        width: '40px',
                                        height: '40px',
                                        borderRadius: '50%',
                                        backgroundColor: getIntegrationColor(integration.integration_name),
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        marginRight: '15px'
                                    }}>
                                        {getIntegrationIcon(integration.integration_name)}
                                    </div>
                                    <div>
                                        <h3 style={{ margin: '0 0 5px 0', color: '#333' }}>
                                            {getIntegrationName(integration.integration_name)}
                                        </h3>
                                        <p style={{ margin: '0', color: '#666', fontSize: '14px' }}>
                                            {integration.status === 'connected' ? 'Connected' : 'Disconnected'}
                                        </p>
                                    </div>
                                </div>
                                <p style={{ color: '#666', fontSize: '14px', margin: '0' }}>
                                    {getIntegrationDescription(integration.integration_name)}
                                </p>
                            </div>
                        ))}
                    </div>
                )}
            </div>
            <ChatbotWidget token={token} />
        </div>
    );
}

const getIntegrationColor = (integrationName) => {
    switch (integrationName) {
        case 'gmail': return '#4285f4';
        case 'calendar': return '#34a853';
        default: return '#6c757d';
    }
};

const getIntegrationIcon = (integrationName) => {
    switch (integrationName) {
        case 'gmail':
            return (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="white">
                    <path d="M20 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 4l-8 5-8-5V6l8 5 8-5v2z"/>
                </svg>
            );
        case 'calendar':
            return (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="white">
                    <path d="M19 3h-1V1h-2v2H8V1H6v2H5c-1.11 0-1.99.9-1.99 2L3 19c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V8h14v11zM7 10h5v5H7z"/>
                </svg>
            );
        default:
            return (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="white">
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                </svg>
            );
    }
};

const getIntegrationName = (integrationName) => {
    switch (integrationName) {
        case 'gmail': return 'Gmail';
        case 'calendar': return 'Google Calendar';
        default: return 'Unknown';
    }
};

const getIntegrationDescription = (integrationName) => {
    switch (integrationName) {
        case 'gmail': return 'Send, receive, and manage your emails';
        case 'calendar': return 'Schedule and manage your events';
        default: return 'Integration description';
    }
};

export default DashboardPage;
