import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import api from '../services/api';

function SendEmailPage() {
    const navigate = useNavigate();
    const location = useLocation();
    const queryParams = new URLSearchParams(location.search);

    const replyToId = queryParams.get('replyTo');
    const threadId = queryParams.get('threadId');
    const initialSubject = queryParams.get('subject') || '';
    const initialTo = queryParams.get('to') || '';

    const [toEmail, setToEmail] = useState(initialTo);
    const [subject, setSubject] = useState(initialSubject);
    const [messageText, setMessageText] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [success, setSuccess] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError(null);
        setSuccess(false);

        try {
            const payload = {
                to_email: toEmail,
                subject: subject,
                message_text: messageText,
                thread_id: threadId
            };
            await api.post('/gmail/send', payload);
            setSuccess(true);
            setMessageText('');
            if (!replyToId) {
                setToEmail('');
                setSubject('');
            }
        } catch (err) {
            setError('Failed to send email. Please check your inputs and try again.');
            console.error('Send email error:', err);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={{ padding: '20px', maxWidth: '600px', margin: 'auto', fontFamily: 'Arial, sans-serif' }}>
            <h2 style={{ textAlign: 'center', color: '#333' }}>{replyToId ? 'Reply to Email' : 'Compose New Email'}</h2>
            <form onSubmit={handleSubmit} style={{ border: '1px solid #ddd', padding: '20px', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
                <div style={{ marginBottom: '15px' }}>
                    <label htmlFor="toEmail" style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>To:</label>
                    <input
                        type="email"
                        id="toEmail"
                        value={toEmail}
                        onChange={(e) => setToEmail(e.target.value)}
                        required
                        style={{ width: 'calc(100% - 22px)', padding: '10px', border: '1px solid #ccc', borderRadius: '4px' }}
                    />
                </div>
                <div style={{ marginBottom: '15px' }}>
                    <label htmlFor="subject" style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Subject:</label>
                    <input
                        type="text"
                        id="subject"
                        value={subject}
                        onChange={(e) => setSubject(e.target.value)}
                        required
                        style={{ width: 'calc(100% - 22px)', padding: '10px', border: '1px solid #ccc', borderRadius: '4px' }}
                    />
                </div>
                <div style={{ marginBottom: '15px' }}>
                    <label htmlFor="messageText" style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Message:</label>
                    <textarea
                        id="messageText"
                        value={messageText}
                        onChange={(e) => setMessageText(e.target.value)}
                        rows="10"
                        required
                        style={{ width: 'calc(100% - 22px)', padding: '10px', border: '1px solid #ccc', borderRadius: '4px', resize: 'vertical' }}
                    ></textarea>
                </div>
                {error && <p style={{ color: '#dc3545', marginBottom: '10px' }}>Error: {error}</p>}
                {success && <p style={{ color: '#28a745', marginBottom: '10px' }}>Email sent successfully!</p>}
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <button
                        type="submit"
                        disabled={loading}
                        style={{ padding: '10px 20px', backgroundColor: '#007bff', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
                    >
                        {loading ? 'Sending...' : 'Send Email'}
                    </button>
                    <button
                        type="button"
                        onClick={() => navigate('/dashboard')}
                        style={{ padding: '10px 20px', backgroundColor: '#6c757d', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
                    >
                        Cancel
                    </button>
                </div>
            </form>
        </div>
    );
}

export default SendEmailPage; 