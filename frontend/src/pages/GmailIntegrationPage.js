import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { tenantApi } from '../services/api';

function GmailIntegrationPage() {
    const navigate = useNavigate();
    const { tenantId, plexusToken } = useAuth();
    const [searchQuery, setSearchQuery] = useState('');
    const [searchResults, setSearchResults] = useState([]);
    const [lastEmail, setLastEmail] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [connectionStatus, setConnectionStatus] = useState('checking');

    useEffect(() => {
        if (tenantId && plexusToken) {
            checkGmailConnection();
        } else {
            setError('Tenant configuration not found. Please try logging in again.');
            setConnectionStatus('error');
        }
    }, [tenantId, plexusToken]);

    const checkGmailConnection = async () => {
        try {
            setLoading(true);
            console.log('Checking Gmail connection for tenant:', tenantId);

            const status = await tenantApi.getGmailStatus();
            console.log('Gmail status:', status);

            if (status.connected) {
                setConnectionStatus('connected');
            } else {
                setConnectionStatus('disconnected');
                setError('Gmail is not connected for this tenant. Please connect Gmail from the dashboard first.');
            }
        } catch (error) {
            console.error('Error checking Gmail connection:', error);
            setConnectionStatus('error');
            setError('Failed to check Gmail connection status. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    const handleConnectGmail = async () => {
        try {
            setLoading(true);
            setError('');

            console.log('Starting Gmail OAuth flow for tenant:', tenantId);
            const response = await tenantApi.startGmailOAuth();

            if (response.auth_url) {
                // Redirect to OAuth flow
                window.location.href = response.auth_url;
            } else {
                setError('Failed to initiate Gmail OAuth flow. Please try again.');
            }
        } catch (error) {
            console.error('Error starting Gmail OAuth:', error);
            setError('Failed to start Gmail connection. Please try again.');
            setLoading(false);
        }
    };

    const handleSearch = async () => {
        if (connectionStatus !== 'connected') {
            setError('Gmail is not connected. Please connect Gmail first.');
            return;
        }

        setLoading(true);
        setError('');
        try {
            // This would use tenant-level Gmail search API
            const response = await tenantApi.searchGmailEmails(tenantId, searchQuery);
            setSearchResults(response.data || []);
            setLastEmail(null);
        } catch (err) {
            console.error('Gmail search error:', err);
            setError('Failed to search emails. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    const handleGetLastEmail = async () => {
        if (connectionStatus !== 'connected') {
            setError('Gmail is not connected. Please connect Gmail first.');
            return;
        }

        setLoading(true);
        setError('');
        try {
            // This would use tenant-level Gmail API
            const response = await tenantApi.getLastGmailEmail(tenantId);
            setLastEmail(response.data);
            setSearchResults([]);
        } catch (err) {
            console.error('Gmail last email error:', err);
            setError('Failed to retrieve last email. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    const handleComposeNewEmail = () => {
        if (connectionStatus !== 'connected') {
            setError('Gmail is not connected. Please connect Gmail first.');
            return;
        }
        navigate('/send-email');
    };

    const handleReplyEmail = (emailId, threadId, subject, sender) => {
        if (connectionStatus !== 'connected') {
            setError('Gmail is not connected. Please connect Gmail first.');
            return;
        }
        navigate(`/send-email?replyTo=${emailId}&threadId=${threadId}&subject=Re: ${subject}&to=${sender}`);
    };

    const handleBack = () => {
        navigate('/dashboard');
    };

    if (loading && connectionStatus === 'checking') {
        return (
            <div style={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                height: '100vh',
                flexDirection: 'column'
            }}>
                <div style={{ marginBottom: '20px' }}>Checking Gmail connection...</div>
                <div style={{ fontSize: '14px', color: '#666' }}>
                    Tenant: {tenantId}
                </div>
            </div>
        );
    }

    return (
        <div style={{
            padding: '20px',
            maxWidth: '1000px',
            margin: 'auto',
            fontFamily: 'Arial, sans-serif'
        }}>
            <div style={{
                display: 'flex',
                alignItems: 'center',
                marginBottom: '30px',
                borderBottom: '1px solid #eee',
                paddingBottom: '20px'
            }}>
                <button
                    onClick={handleBack}
                    style={{
                        background: 'none',
                        border: 'none',
                        fontSize: '18px',
                        cursor: 'pointer',
                        marginRight: '15px',
                        color: '#666'
                    }}
                >
                    ←
                </button>
                <div style={{ display: 'flex', alignItems: 'center', flex: 1 }}>
                    <div style={{
                        width: '40px',
                        height: '40px',
                        borderRadius: '50%',
                        backgroundColor: '#4285f4',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        marginRight: '15px'
                    }}>
                        📧
                    </div>
                    <div>
                        <h1 style={{ color: '#333', margin: '0 0 5px 0' }}>
                            Gmail Integration
                        </h1>
                        <p style={{ color: '#666', margin: '0' }}>
                            Tenant: {tenantId} • Status: {connectionStatus}
                        </p>
                    </div>
                </div>
                <div style={{
                    padding: '8px 12px',
                    borderRadius: '12px',
                    fontSize: '12px',
                    fontWeight: 'bold',
                    backgroundColor: connectionStatus === 'connected' ? '#d4edda' : '#f8d7da',
                    color: connectionStatus === 'connected' ? '#155724' : '#721c24'
                }}>
                    {connectionStatus === 'connected' ? '🟢 Connected' :
                     connectionStatus === 'error' ? '🔴 Error' : '🔘 Disconnected'}
                </div>
            </div>

            {error && (
                <div style={{
                    backgroundColor: '#ffebee',
                    color: '#c62828',
                    padding: '15px',
                    borderRadius: '5px',
                    marginBottom: '20px',
                    fontSize: '14px'
                }}>
                    {error}
                    <button
                        onClick={() => setError('')}
                        style={{
                            float: 'right',
                            background: 'none',
                            border: 'none',
                            color: '#c62828',
                            cursor: 'pointer',
                            fontSize: '16px'
                        }}
                    >
                        ×
                    </button>
                </div>
            )}

            {connectionStatus !== 'connected' && (
                <div style={{
                    textAlign: 'center',
                    padding: '40px',
                    backgroundColor: '#f8f9fa',
                    borderRadius: '10px',
                    border: '2px dashed #dee2e6',
                    marginBottom: '30px'
                }}>
                    <div style={{ fontSize: '48px', marginBottom: '20px' }}>📧</div>
                    <h3 style={{ color: '#6c757d', marginBottom: '15px' }}>
                        Gmail Not Connected
                    </h3>
                    <p style={{ color: '#6c757d', marginBottom: '20px' }}>
                        Connect your Gmail account to access email features
                    </p>
                    <button
                        onClick={handleConnectGmail}
                        disabled={loading}
                        style={{
                            padding: '12px 24px',
                            backgroundColor: '#4285f4',
                            color: 'white',
                            border: 'none',
                            borderRadius: '5px',
                            cursor: loading ? 'not-allowed' : 'pointer',
                            fontSize: '16px',
                            opacity: loading ? 0.7 : 1
                        }}
                    >
                        {loading ? 'Connecting...' : 'Connect Gmail'}
                    </button>
                </div>
            )}

            {connectionStatus === 'connected' && (
                <>
                    <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
                        gap: '20px',
                        marginBottom: '30px'
                    }}>
                        <div style={{
                            backgroundColor: 'white',
                            border: '1px solid #dee2e6',
                            borderRadius: '10px',
                            padding: '20px',
                            textAlign: 'center',
                            cursor: 'pointer',
                            transition: 'all 0.2s ease'
                        }}
                        onClick={handleComposeNewEmail}
                        onMouseEnter={(e) => {
                            e.target.style.transform = 'translateY(-2px)';
                            e.target.style.boxShadow = '0 4px 8px rgba(0,0,0,0.15)';
                        }}
                        onMouseLeave={(e) => {
                            e.target.style.transform = 'translateY(0)';
                            e.target.style.boxShadow = '0 2px 4px rgba(0,0,0,0.1)';
                        }}
                        >
                            <div style={{ fontSize: '48px', marginBottom: '15px' }}>✉️</div>
                            <h3 style={{ margin: '0 0 10px 0', color: '#333' }}>Compose Email</h3>
                            <p style={{ margin: '0', color: '#666', fontSize: '14px' }}>
                                Write and send new emails
                            </p>
                        </div>

                        <div style={{
                            backgroundColor: 'white',
                            border: '1px solid #dee2e6',
                            borderRadius: '10px',
                            padding: '20px',
                            textAlign: 'center',
                            cursor: 'pointer',
                            transition: 'all 0.2s ease'
                        }}
                        onClick={handleGetLastEmail}
                        onMouseEnter={(e) => {
                            e.target.style.transform = 'translateY(-2px)';
                            e.target.style.boxShadow = '0 4px 8px rgba(0,0,0,0.15)';
                        }}
                        onMouseLeave={(e) => {
                            e.target.style.transform = 'translateY(0)';
                            e.target.style.boxShadow = '0 2px 4px rgba(0,0,0,0.1)';
                        }}
                        >
                            <div style={{ fontSize: '48px', marginBottom: '15px' }}>📥</div>
                            <h3 style={{ margin: '0 0 10px 0', color: '#333' }}>Last Email</h3>
                            <p style={{ margin: '0', color: '#666', fontSize: '14px' }}>
                                View your most recent email
                            </p>
                        </div>

                        <div style={{
                            backgroundColor: 'white',
                            border: '1px solid #dee2e6',
                            borderRadius: '10px',
                            padding: '20px',
                            textAlign: 'center',
                            cursor: 'pointer',
                            transition: 'all 0.2s ease'
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
                            <div style={{ fontSize: '48px', marginBottom: '15px' }}>📊</div>
                            <h3 style={{ margin: '0 0 10px 0', color: '#333' }}>Email Analytics</h3>
                            <p style={{ margin: '0', color: '#666', fontSize: '14px' }}>
                                View email statistics and insights
                            </p>
                        </div>
                    </div>

                    <div style={{ marginBottom: '30px' }}>
                        <h2 style={{ color: '#333', marginBottom: '20px' }}>Search Emails</h2>
                        <div style={{
                            display: 'flex',
                            gap: '10px',
                            marginBottom: '20px'
                        }}>
                            <input
                                type="text"
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                placeholder="Enter search query (e.g., from:sender@example.com, subject:report)"
                                style={{
                                    flex: 1,
                                    padding: '12px',
                                    border: '1px solid #ddd',
                                    borderRadius: '5px',
                                    fontSize: '16px'
                                }}
                                disabled={loading}
                            />
                            <button
                                onClick={handleSearch}
                                disabled={loading}
                                style={{
                                    padding: '12px 24px',
                                    backgroundColor: '#4285f4',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '5px',
                                    cursor: loading ? 'not-allowed' : 'pointer',
                                    fontSize: '16px',
                                    opacity: loading ? 0.7 : 1
                                }}
                            >
                                {loading ? 'Searching...' : 'Search'}
                            </button>
                        </div>
                    </div>

                    {lastEmail && (
                        <div style={{
                            border: '1px solid #4285f4',
                            padding: '20px',
                            borderRadius: '10px',
                            marginBottom: '20px',
                            backgroundColor: '#f8f9ff'
                        }}>
                            <h3 style={{ color: '#4285f4', marginBottom: '15px' }}>Last Received Email:</h3>
                            <p><strong>From:</strong> {lastEmail.sender}</p>
                            <p><strong>Subject:</strong> {lastEmail.subject}</p>
                            <p><strong>Date:</strong> {new Date(lastEmail.date).toLocaleString()}</p>
                            <p><strong>Snippet:</strong> {lastEmail.snippet}</p>
                            <button
                                onClick={() => handleReplyEmail(lastEmail.id, lastEmail.threadId, lastEmail.subject, lastEmail.sender)}
                                style={{
                                    padding: '8px 16px',
                                    backgroundColor: '#ffc107',
                                    color: 'black',
                                    border: 'none',
                                    borderRadius: '5px',
                                    cursor: 'pointer',
                                    marginTop: '10px'
                                }}
                            >
                                Reply
                            </button>
                        </div>
                    )}

                    {searchResults.length > 0 && (
                        <div style={{
                            border: '1px solid #dee2e6',
                            padding: '20px',
                            borderRadius: '10px',
                            backgroundColor: 'white'
                        }}>
                            <h3 style={{ color: '#333', marginBottom: '15px' }}>Search Results:</h3>
                            {searchResults.map((email) => (
                                <div key={email.id} style={{
                                    borderBottom: '1px solid #eee',
                                    padding: '15px 0',
                                    marginBottom: '15px'
                                }}>
                                    <p><strong>From:</strong> {email.sender}</p>
                                    <p><strong>Subject:</strong> {email.subject}</p>
                                    <p><strong>Date:</strong> {new Date(email.date).toLocaleString()}</p>
                                    <p><strong>Snippet:</strong> {email.snippet}</p>
                                    <button
                                        onClick={() => handleReplyEmail(email.id, email.threadId, email.subject, email.sender)}
                                        style={{
                                            padding: '8px 16px',
                                            backgroundColor: '#ffc107',
                                            color: 'black',
                                            border: 'none',
                                            borderRadius: '5px',
                                            cursor: 'pointer',
                                            marginTop: '10px'
                                        }}
                                    >
                                        Reply
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}
                </>
            )}
        </div>
    );
}

export default GmailIntegrationPage;
