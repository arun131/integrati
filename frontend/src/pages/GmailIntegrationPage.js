import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate, useParams } from 'react-router-dom';
import api from '../services/api';

function GmailIntegrationPage() {
    const { user } = useAuth();
    const navigate = useNavigate();
    const { integrationId } = useParams();
    const [searchQuery, setSearchQuery] = useState('');
    const [searchResults, setSearchResults] = useState([]);
    const [lastEmail, setLastEmail] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const handleSearch = async () => {
        setLoading(true);
        setError('');
        try {
            const response = await api.post('/integrations/gmail/api/search', { query: searchQuery });
            setSearchResults(response.data);
        } catch (err) {
            setError('Failed to search emails. Please try again.');
            console.error('Search error:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleGetLastEmail = async () => {
        setLoading(true);
        setError('');
        try {
            const response = await api.get('/integrations/gmail/api/last-received');
            setLastEmail(response.data);
            setSearchResults([]);
        } catch (err) {
            setError('Failed to retrieve last email. Please try again.');
            console.error('Get last email error:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleComposeNewEmail = () => {
        navigate('/send-email');
    };

    const handleReplyEmail = (emailId, threadId, subject, sender) => {
        navigate(`/send-email?replyTo=${emailId}&threadId=${threadId}&subject=Re: ${subject}&to=${sender}`);
    };

    const handleBack = () => {
        navigate('/dashboard');
    };

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
                            Manage your emails and communications
                        </p>
                    </div>
                </div>
            </div>

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
                </div>
            )}

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
        </div>
    );
}

export default GmailIntegrationPage; 