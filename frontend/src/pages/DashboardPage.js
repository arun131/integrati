import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useApprovals } from '../context/ApprovalContext';
import { useNotifications } from '../context/NotificationContext';
import { useNavigate, useLocation } from 'react-router-dom';
import { tenantApi } from '../services/api';
import ChatbotWidget from '../components/ChatbotWidget';
import NotificationPanel from '../components/NotificationPanel';

function DashboardPage() {
    const { user, logout, tenantId, plexusToken, tenantRegistrationError } = useAuth();
    const { pendingCount } = useApprovals();
    const { unreadCount } = useNotifications();
    const navigate = useNavigate();
    const location = useLocation();
    const [integrations, setIntegrations] = useState({
        gmail: { status: 'available', tools: [] },
        calendar: { status: 'available', tools: [] }
    });
    const [commonTools] = useState([
        { name: 'Calculator', description: 'Perform mathematical calculations', icon: '🧮' },
        { name: 'Text Processor', description: 'Process and manipulate text', icon: '📝' }
    ]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [successMessage, setSuccessMessage] = useState('');

    useEffect(() => {
        if (tenantId && plexusToken) {
            loadIntegrationStatus();
        } else if (!tenantId) {
            setError('Tenant not properly configured. Please try logging in again.');
            setLoading(false);
        } else {
            setLoading(false);
        }
    }, [tenantId, plexusToken]);

    // Check for success messages from OAuth redirects
    useEffect(() => {
        const queryParams = new URLSearchParams(location.search);
        const gmailConnected = queryParams.get('gmail_connected');
        const calendarConnected = queryParams.get('calendar_connected');

        if (gmailConnected === 'true') {
            setSuccessMessage('Gmail integration connected successfully!');
            // Clear the URL parameter
            navigate('/dashboard', { replace: true });
            // Reload integration status to show the new connection
            if (tenantId && plexusToken) {
                loadIntegrationStatus();
            }
            // Clear success message after 5 seconds
            setTimeout(() => {
                setSuccessMessage('');
            }, 5000);
        }

        if (calendarConnected === 'true') {
            setSuccessMessage('Calendar integration connected successfully!');
            // Clear the URL parameter
            navigate('/dashboard', { replace: true });
            // Reload integration status to show the new connection
            if (tenantId && plexusToken) {
                loadIntegrationStatus();
            }
            // Clear success message after 5 seconds
            setTimeout(() => {
                setSuccessMessage('');
            }, 5000);
        }
    }, [location.search, tenantId, plexusToken]);

    const loadIntegrationStatus = async () => {
        try {
            setLoading(true);
            setError('');

            console.log('Loading integration status for tenant:', tenantId);

            // Load Gmail status
            try {
                const gmailStatus = await tenantApi.getGmailStatus();
                console.log('=== GMAIL STATUS DEBUG ===');
                console.log('Gmail status response:', gmailStatus);
                console.log('Gmail status.status:', gmailStatus.status);
                console.log('Gmail status.connected:', gmailStatus.connected);
                console.log('Gmail final status:', gmailStatus.status === 'connected' ? 'connected' : 'available');
                console.log('=== END GMAIL DEBUG ===');

                setIntegrations(prev => ({
                    ...prev,
                    gmail: {
                        status: gmailStatus.status === 'connected' ? 'connected' : 'available',
                        tools: gmailStatus.status === 'connected' ? [
                            { name: 'Send Email', description: 'Compose and send emails', icon: '📧' },
                            { name: 'Search Emails', description: 'Search through your emails', icon: '🔍' },
                            { name: 'Read Latest Email', description: 'Get your most recent email', icon: '📥' }
                        ] : []
                    }
                }));
            } catch (error) {
                console.log('Gmail status not available:', error.message);
                // Keep default 'available' status
            }

            // Load Calendar status
            try {
                const calendarStatus = await tenantApi.getCalendarStatus();
                console.log('=== CALENDAR STATUS DEBUG ===');
                console.log('Calendar status response:', calendarStatus);
                console.log('Calendar status.status:', calendarStatus.status);
                console.log('Calendar status.connected:', calendarStatus.connected);
                console.log('Calendar final status:', calendarStatus.connected ? 'connected' : 'available');
                console.log('=== END CALENDAR DEBUG ===');

                setIntegrations(prev => ({
                    ...prev,
                    calendar: {
                        status: calendarStatus.status === 'connected' ? 'connected' : 'available',
                        tools: calendarStatus.status === 'connected' ? [
                            { name: 'Create Event', description: 'Schedule new events', icon: '📅' },
                            { name: 'View Events', description: 'View your calendar events', icon: '👁️' },
                            { name: 'Update Event', description: 'Modify existing events', icon: '✏️' },
                            { name: 'Upcoming Events', description: 'Get upcoming events', icon: '⏰' }
                        ] : []
                    }
                }));
            } catch (error) {
                console.log('Calendar status not available:', error.message);
                // Keep default 'available' status
            }

        } catch (error) {
            console.error('Error loading integration status:', error);
            setError('Failed to load integration status. Please try refreshing the page.');
        } finally {
            setLoading(false);
        }
    };

    const handleConnectIntegration = async (integrationType) => {
        try {
            setLoading(true);
            setError('');

            console.log(`Starting ${integrationType} OAuth flow for tenant:`, tenantId);

            if (integrationType === 'gmail') {
                // Start Gmail OAuth flow
                const response = await tenantApi.startGmailOAuth();
                if (response.auth_url) {
                    // Store the current token in localStorage for the OAuth flow
                    const plexusToken = localStorage.getItem('plexus_user_auth_token');
                    if (plexusToken) {
                        // Add token as query parameter to the auth URL
                        const separator = response.auth_url.includes('?') ? '&' : '?';
                        const authUrlWithToken = `${response.auth_url}${separator}token=${encodeURIComponent(plexusToken)}`;
                        window.location.href = authUrlWithToken;
                    } else {
                        window.location.href = response.auth_url;
                    }
                }
            } else if (integrationType === 'calendar') {
                // Start Calendar OAuth flow
                const response = await tenantApi.startCalendarOAuth();
                if (response.auth_url) {
                    // Store the current token in localStorage for the OAuth flow
                    const plexusToken = localStorage.getItem('plexus_user_auth_token');
                    if (plexusToken) {
                        // Add token as query parameter to the auth URL
                        const separator = response.auth_url.includes('?') ? '&' : '?';
                        const authUrlWithToken = `${response.auth_url}${separator}token=${encodeURIComponent(plexusToken)}`;
                        window.location.href = authUrlWithToken;
                    } else {
                        window.location.href = response.auth_url;
                    }
                }
            }
        } catch (error) {
            console.error(`Error starting ${integrationType} OAuth:`, error);
            setError(`Failed to start ${integrationType} connection. Please try again.`);
            setLoading(false);
        }
    };

    const handleDisconnectIntegration = async (integrationType) => {
        try {
            setLoading(true);
            setError('');

            if (integrationType === 'gmail') {
                await tenantApi.disconnectGmail();
                setIntegrations(prev => ({
                    ...prev,
                    gmail: { status: 'available', tools: [] }
                }));
            } else if (integrationType === 'calendar') {
                await tenantApi.disconnectCalendar(tenantId);
                setIntegrations(prev => ({
                    ...prev,
                    calendar: { status: 'available', tools: [] }
                }));
            }

            console.log(`${integrationType} disconnected successfully`);
        } catch (error) {
            console.error(`Error disconnecting ${integrationType}:`, error);
            setError(`Failed to disconnect ${integrationType}. Please try again.`);
        } finally {
            setLoading(false);
        }
    };

    const handleToolClick = (toolName, integrationType) => {
        // Navigate to specific tool pages or trigger tool actions
        if (integrationType === 'gmail') {
            if (toolName === 'Send Email') {
                navigate('/send-email');
            } else {
                navigate('/integration/gmail');
            }
        } else if (integrationType === 'calendar') {
            navigate('/integration/calendar');
        }
        // Common tools can be handled here too
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
                height: '100vh',
                flexDirection: 'column'
            }}>
                <div style={{ marginBottom: '20px' }}>Loading your dashboard...</div>
                <div style={{ fontSize: '14px', color: '#666' }}>
                    Setting up integrations and tools
                </div>
            </div>
        );
    }

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
                    <p style={{ color: '#666', margin: '0', display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <span>Tenant: {tenantId} • Manage your integrations and services</span>
                        {unreadCount > 0 && (
                            <span style={{
                                backgroundColor: '#007bff',
                                color: 'white',
                                borderRadius: '12px',
                                padding: '2px 8px',
                                fontSize: '12px',
                                fontWeight: 'bold'
                            }}>
                                {unreadCount} new notification{unreadCount > 1 ? 's' : ''}
                            </span>
                        )}
                    </p>
                </div>
                <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                    <button
                        onClick={() => navigate('/approvals')}
                        style={{
                            padding: '10px 20px',
                            backgroundColor: '#007bff',
                            color: 'white',
                            border: 'none',
                            borderRadius: '5px',
                            cursor: 'pointer',
                            fontSize: '14px',
                            position: 'relative',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px'
                        }}
                    >
                        🔐 Approvals
                        {pendingCount > 0 && (
                            <span style={{
                                backgroundColor: '#dc3545',
                                color: 'white',
                                borderRadius: '50%',
                                padding: '2px 6px',
                                fontSize: '12px',
                                fontWeight: 'bold',
                                minWidth: '18px',
                                textAlign: 'center'
                            }}>
                                {pendingCount}
                            </span>
                        )}
                    </button>
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
            </div>

            {/* Show tenant registration error if present */}
            {tenantRegistrationError && (
                <div style={{ color: 'red', marginBottom: '1rem' }}>
                    {tenantRegistrationError}
                </div>
            )}
            {/* Existing error display */}
            {error && (
                <div style={{ color: 'red', marginBottom: '1rem' }}>
                    {error}
                </div>
            )}
            {/* Success message display */}
            {successMessage && (
                <div style={{ color: 'green', marginBottom: '1rem', padding: '10px', backgroundColor: '#d4edda', borderRadius: '4px', border: '1px solid #c3e6cb' }}>
                    {successMessage}
                </div>
            )}

            {/* Notifications Section */}
            <NotificationPanel />

            {/* Common Tools Section */}
            <div style={{ marginBottom: '40px' }}>
                <h2 style={{ color: '#333', marginBottom: '20px' }}>Common Tools</h2>
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))',
                    gap: '15px'
                }}>
                    {commonTools.map((tool) => (
                        <div
                            key={tool.name}
                            onClick={() => handleToolClick(tool.name, 'common')}
                            style={{
                                backgroundColor: 'white',
                                border: '1px solid #dee2e6',
                                borderRadius: '8px',
                                padding: '15px',
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
                            <div style={{ fontSize: '24px', marginBottom: '10px' }}>{tool.icon}</div>
                            <h4 style={{ margin: '0 0 8px 0', color: '#333' }}>{tool.name}</h4>
                            <p style={{ margin: '0', color: '#666', fontSize: '14px' }}>{tool.description}</p>
                        </div>
                    ))}
                </div>
            </div>

            {/* Integrations Section */}
            <div style={{ marginBottom: '30px' }}>
                <h2 style={{ color: '#333', marginBottom: '20px' }}>Integrations</h2>

                <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
                    gap: '20px'
                }}>
                    {Object.entries(integrations).map(([key, integration]) => (
                        <div
                            key={key}
                            style={{
                                backgroundColor: 'white',
                                border: `2px solid ${getStatusColor(integration.status)}`,
                                borderRadius: '10px',
                                padding: '20px',
                                transition: 'all 0.2s ease',
                                boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
                            }}
                        >
                            <div style={{ display: 'flex', alignItems: 'center', marginBottom: '15px' }}>
                                <div style={{
                                    width: '40px',
                                    height: '40px',
                                    borderRadius: '50%',
                                    backgroundColor: getIntegrationColor(key),
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    marginRight: '15px'
                                }}>
                                    {getIntegrationIcon(key)}
                                </div>
                                <div style={{ flex: 1 }}>
                                    <h3 style={{ margin: '0 0 5px 0', color: '#333' }}>
                                        {getIntegrationName(key)}
                                    </h3>
                                    <div style={{ display: 'flex', alignItems: 'center' }}>
                                        <span style={{
                                            width: '10px',
                                            height: '10px',
                                            borderRadius: '50%',
                                            backgroundColor: getStatusColor(integration.status),
                                            marginRight: '8px'
                                        }}></span>
                                        <span style={{ color: '#666', fontSize: '14px' }}>
                                            {integration.status === 'connected' ? 'Connected' : 'Available'}
                                        </span>
                                    </div>
                                </div>
                            </div>

                            <p style={{ color: '#666', fontSize: '14px', marginBottom: '15px' }}>
                                {getIntegrationDescription(key)}
                            </p>

                            {/* Integration Tools */}
                            {integration.tools.length > 0 && (
                                <div style={{ marginBottom: '15px' }}>
                                    <h5 style={{ margin: '0 0 10px 0', color: '#333' }}>Available Tools:</h5>
                                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                                        {integration.tools.map((tool) => (
                                            <span
                                                key={tool.name}
                                                onClick={() => handleToolClick(tool.name, key)}
                                                style={{
                                                    backgroundColor: '#f8f9fa',
                                                    padding: '4px 8px',
                                                    borderRadius: '12px',
                                                    fontSize: '12px',
                                                    color: '#495057',
                                                    cursor: 'pointer',
                                                    border: '1px solid #dee2e6'
                                                }}
                                                title={tool.description}
                                            >
                                                {tool.icon} {tool.name}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Action Button */}
                            <button
                                onClick={() => integration.status === 'connected'
                                    ? handleDisconnectIntegration(key)
                                    : handleConnectIntegration(key)
                                }
                                disabled={loading}
                                style={{
                                    width: '100%',
                                    padding: '10px',
                                    backgroundColor: integration.status === 'connected' ? '#dc3545' : '#28a745',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '5px',
                                    cursor: loading ? 'not-allowed' : 'pointer',
                                    fontSize: '14px',
                                    opacity: loading ? 0.7 : 1
                                }}
                            >
                                {integration.status === 'connected' ? 'Disconnect' : 'Connect'}
                            </button>
                        </div>
                    ))}
                </div>
            </div>

            <ChatbotWidget token={plexusToken} />
        </div>
    );
}

const getStatusColor = (status) => {
    switch (status) {
        case 'connected': return '#28a745';
        case 'error': return '#dc3545';
        default: return '#6c757d';
    }
};

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
        case 'gmail': return 'Send, receive, and manage your emails with AI assistance';
        case 'calendar': return 'Schedule and manage your events and meetings';
        default: return 'Integration description';
    }
};

export default DashboardPage;
