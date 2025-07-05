import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { collection, addDoc } from 'firebase/firestore';
import { db } from '../firebase';

function AddIntegrationPage() {
    const { user } = useAuth();
    const navigate = useNavigate();
    const [selectedIntegration, setSelectedIntegration] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');

    const availableIntegrations = [
        {
            id: 'gmail',
            name: 'Gmail',
            description: 'Send, receive, and manage your emails',
            icon: '📧',
            color: '#4285f4'
        },
        {
            id: 'calendar',
            name: 'Google Calendar',
            description: 'Schedule and manage your events',
            icon: '📅',
            color: '#34a853'
        }
    ];

    const handleIntegrationSelect = (integrationId) => {
        setSelectedIntegration(integrationId);
    };

    const handleAddIntegration = async () => {
        if (!selectedIntegration) {
            setError('Please select an integration');
            return;
        }

        setLoading(true);
        setError('');
        setSuccess('');

        try {
            // Redirect to backend OAuth endpoint for the selected integration
            let backendUrl = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';
            if (selectedIntegration === 'gmail') {
                window.location.href = `${backendUrl}/integrations/gmail/auth/login`;
            } else if (selectedIntegration === 'calendar') {
                window.location.href = `${backendUrl}/integrations/calendar/auth/login`;
            } else {
                setError('Unknown integration type.');
            }
        } catch (error) {
            console.error('Error adding integration:', error);
            setError('Failed to add integration. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    const getIntegrationName = (type) => {
        switch (type) {
            case 'gmail': return 'Gmail';
            case 'calendar': return 'Google Calendar';
            default: return 'Integration';
        }
    };

    const handleBack = () => {
        navigate('/dashboard');
    };

    return (
        <div style={{ 
            padding: '20px', 
            maxWidth: '800px', 
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
                <div>
                    <h1 style={{ color: '#333', margin: '0 0 5px 0' }}>
                        Add Integration
                    </h1>
                    <p style={{ color: '#666', margin: '0' }}>
                        Choose a service to connect to your account
                    </p>
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

            {success && (
                <div style={{
                    backgroundColor: '#e8f5e8',
                    color: '#2e7d32',
                    padding: '15px',
                    borderRadius: '5px',
                    marginBottom: '20px',
                    fontSize: '14px'
                }}>
                    {success}
                </div>
            )}

            <div style={{ marginBottom: '30px' }}>
                <h2 style={{ color: '#333', marginBottom: '20px' }}>
                    Available Integrations
                </h2>
                
                <div style={{
                    display: 'grid',
                    gap: '15px'
                }}>
                    {availableIntegrations.map((integration) => (
                        <div
                            key={integration.id}
                            onClick={() => handleIntegrationSelect(integration.id)}
                            style={{
                                border: selectedIntegration === integration.id 
                                    ? `2px solid ${integration.color}` 
                                    : '2px solid #e0e0e0',
                                borderRadius: '10px',
                                padding: '20px',
                                cursor: 'pointer',
                                backgroundColor: selectedIntegration === integration.id 
                                    ? `${integration.color}10` 
                                    : 'white',
                                transition: 'all 0.2s ease'
                            }}
                        >
                            <div style={{ display: 'flex', alignItems: 'center' }}>
                                <div style={{
                                    width: '50px',
                                    height: '50px',
                                    borderRadius: '50%',
                                    backgroundColor: integration.color,
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    marginRight: '20px',
                                    fontSize: '24px'
                                }}>
                                    {integration.icon}
                                </div>
                                <div style={{ flex: 1 }}>
                                    <h3 style={{ 
                                        margin: '0 0 5px 0', 
                                        color: '#333',
                                        fontSize: '18px'
                                    }}>
                                        {integration.name}
                                    </h3>
                                    <p style={{ 
                                        margin: '0', 
                                        color: '#666',
                                        fontSize: '14px'
                                    }}>
                                        {integration.description}
                                    </p>
                                </div>
                                {selectedIntegration === integration.id && (
                                    <div style={{
                                        width: '20px',
                                        height: '20px',
                                        borderRadius: '50%',
                                        backgroundColor: integration.color,
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        color: 'white',
                                        fontSize: '12px'
                                    }}>
                                        ✓
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                paddingTop: '20px',
                borderTop: '1px solid #eee'
            }}>
                <button
                    onClick={handleBack}
                    style={{
                        padding: '12px 24px',
                        backgroundColor: '#6c757d',
                        color: 'white',
                        border: 'none',
                        borderRadius: '5px',
                        cursor: 'pointer',
                        fontSize: '16px'
                    }}
                >
                    Cancel
                </button>
                <button
                    onClick={handleAddIntegration}
                    disabled={!selectedIntegration || loading}
                    style={{
                        padding: '12px 24px',
                        backgroundColor: selectedIntegration ? '#28a745' : '#ccc',
                        color: 'white',
                        border: 'none',
                        borderRadius: '5px',
                        cursor: selectedIntegration && !loading ? 'pointer' : 'not-allowed',
                        fontSize: '16px',
                        opacity: loading ? 0.7 : 1
                    }}
                >
                    {loading ? 'Adding...' : 'Add Integration'}
                </button>
            </div>
        </div>
    );
}

export default AddIntegrationPage; 