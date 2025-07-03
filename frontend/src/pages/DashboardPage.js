import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';
import { useNavigate } from 'react-router-dom';

function DashboardPage() {
    const { userEmail, logout } = useAuth();
    const navigate = useNavigate();
    const [searchQuery, setSearchQuery] = useState('');
    const [searchResults, setSearchResults] = useState([]);
    const [lastEmail, setLastEmail] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const handleSearch = async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await api.post('/gmail/search', { query: searchQuery });
            setSearchResults(response.data);
        } catch (err) {
            setError('Failed to search emails. Please try again or re-login.');
            console.error('Search error:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleGetLastEmail = async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await api.get('/gmail/last-received');
            setLastEmail(response.data);
            setSearchResults([]);
        } catch (err) {
            setError('Failed to retrieve last email. Please try again or re-login.');
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

    return (
        <div style={{ padding: '20px', maxWidth: '800px', margin: 'auto', fontFamily: 'Arial, sans-serif' }}>
            <h2 style={{ textAlign: 'center', color: '#333' }}>Welcome, {userEmail}!</h2>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '20px' }}>
                <button
                    onClick={handleComposeNewEmail}
                    style={{ padding: '10px 15px', backgroundColor: '#28a745', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
                >
                    Compose New Email
                </button>
                <button
                    onClick={handleGetLastEmail}
                    style={{ padding: '10px 15px', backgroundColor: '#007bff', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
                >
                    Get Last Received Email
                </button>
                <button
                    onClick={logout}
                    style={{ padding: '10px 15px', backgroundColor: '#dc3545', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
                >
                    Logout
                </button>
            </div>

            <div style={{ marginBottom: '30px', border: '1px solid #ddd', padding: '20px', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
                <h3 style={{ color: '#555' }}>Search Inbox</h3>
                <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Enter search query (e.g., from:sender@example.com, subject:report)"
                    style={{ width: 'calc(100% - 22px)', padding: '10px', marginBottom: '10px', border: '1px solid #ccc', borderRadius: '4px' }}
                />
                <button
                    onClick={handleSearch}
                    disabled={loading}
                    style={{ padding: '10px 20px', backgroundColor: '#6c757d', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
                >
                    {loading ? 'Searching...' : 'Search'}
                </button>
            </div>

            {loading && <p style={{ textAlign: 'center', color: '#007bff' }}>Loading...</p>}
            {error && <p style={{ textAlign: 'center', color: '#dc3545' }}>Error: {error}</p>}

            {lastEmail && (
                <div style={{ border: '1px solid #007bff', padding: '15px', borderRadius: '8px', marginBottom: '20px', backgroundColor: '#e7f3ff' }}>
                    <h3 style={{ color: '#007bff' }}>Last Received Email:</h3>
                    <p><strong>From:</strong> {lastEmail.sender}</p>
                    <p><strong>Subject:</strong> {lastEmail.subject}</p>
                    <p><strong>Date:</strong> {new Date(lastEmail.date).toLocaleString()}</p>
                    <p><strong>Snippet:</strong> {lastEmail.snippet}</p>
                    <button
                        onClick={() => handleReplyEmail(lastEmail.id, lastEmail.threadId, lastEmail.subject, lastEmail.sender)}
                        style={{ padding: '8px 12px', backgroundColor: '#ffc107', color: 'black', border: 'none', borderRadius: '5px', cursor: 'pointer', marginTop: '10px' }}
                    >
                        Reply
                    </button>
                </div>
            )}

            {searchResults.length > 0 && (
                <div style={{ border: '1px solid #6c757d', padding: '15px', borderRadius: '8px' }}>
                    <h3 style={{ color: '#6c757d' }}>Search Results:</h3>
                    {searchResults.map((email) => (
                        <div key={email.id} style={{ borderBottom: '1px solid #eee', padding: '10px 0', marginBottom: '10px' }}>
                            <p><strong>From:</strong> {email.sender}</p>
                            <p><strong>Subject:</strong> {email.subject}</p>
                            <p><strong>Date:</strong> {new Date(email.date).toLocaleString()}</p>
                            <p><strong>Snippet:</strong> {email.snippet}</p>
                            <button
                                onClick={() => handleReplyEmail(email.id, email.threadId, email.subject, email.sender)}
                                style={{ padding: '8px 12px', backgroundColor: '#ffc107', color: 'black', border: 'none', borderRadius: '5px', cursor: 'pointer', marginTop: '5px' }}
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

export default DashboardPage; 