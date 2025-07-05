import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate, useParams } from 'react-router-dom';
import api from '../services/api';

function CalendarIntegrationPage() {
    const { user } = useAuth();
    const navigate = useNavigate();
    const { integrationId } = useParams();
    const [events, setEvents] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const handleViewEvents = async () => {
        setLoading(true);
        setError('');
        try {
            const response = await api.get('/integrations/calendar/api/events');
            setEvents(response.data);
        } catch (err) {
            setError('Failed to load events. Please try again.');
            console.error('Load events error:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleCreateEvent = () => {
        navigate('/create-event');
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
                        backgroundColor: '#34a853',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        marginRight: '15px'
                    }}>
                        📅
                    </div>
                    <div>
                        <h1 style={{ color: '#333', margin: '0 0 5px 0' }}>
                            Google Calendar Integration
                        </h1>
                        <p style={{ color: '#666', margin: '0' }}>
                            Manage your events and schedule
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
                onClick={handleCreateEvent}
                onMouseEnter={(e) => {
                    e.target.style.transform = 'translateY(-2px)';
                    e.target.style.boxShadow = '0 4px 8px rgba(0,0,0,0.15)';
                }}
                onMouseLeave={(e) => {
                    e.target.style.transform = 'translateY(0)';
                    e.target.style.boxShadow = '0 2px 4px rgba(0,0,0,0.1)';
                }}
                >
                    <div style={{ fontSize: '48px', marginBottom: '15px' }}>➕</div>
                    <h3 style={{ margin: '0 0 10px 0', color: '#333' }}>Create Event</h3>
                    <p style={{ margin: '0', color: '#666', fontSize: '14px' }}>
                        Schedule a new event or meeting
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
                onClick={handleViewEvents}
                onMouseEnter={(e) => {
                    e.target.style.transform = 'translateY(-2px)';
                    e.target.style.boxShadow = '0 4px 8px rgba(0,0,0,0.15)';
                }}
                onMouseLeave={(e) => {
                    e.target.style.transform = 'translateY(0)';
                    e.target.style.boxShadow = '0 2px 4px rgba(0,0,0,0.1)';
                }}
                >
                    <div style={{ fontSize: '48px', marginBottom: '15px' }}>📋</div>
                    <h3 style={{ margin: '0 0 10px 0', color: '#333' }}>View Events</h3>
                    <p style={{ margin: '0', color: '#666', fontSize: '14px' }}>
                        See your upcoming events
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
                    <div style={{ fontSize: '48px', marginBottom: '15px' }}>⚙️</div>
                    <h3 style={{ margin: '0 0 10px 0', color: '#333' }}>Calendar Settings</h3>
                    <p style={{ margin: '0', color: '#666', fontSize: '14px' }}>
                        Manage calendar preferences
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
                    <h3 style={{ margin: '0 0 10px 0', color: '#333' }}>Calendar Analytics</h3>
                    <p style={{ margin: '0', color: '#666', fontSize: '14px' }}>
                        View calendar usage insights
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

            {loading && (
                <div style={{
                    textAlign: 'center',
                    padding: '20px',
                    color: '#666'
                }}>
                    Loading events...
                </div>
            )}

            {events.length > 0 && (
                <div style={{
                    border: '1px solid #dee2e6',
                    padding: '20px',
                    borderRadius: '10px',
                    backgroundColor: 'white'
                }}>
                    <h3 style={{ color: '#333', marginBottom: '15px' }}>Your Events:</h3>
                    {events.map((event) => (
                        <div key={event.id} style={{
                            borderBottom: '1px solid #eee',
                            padding: '15px 0',
                            marginBottom: '15px'
                        }}>
                            <h4 style={{ margin: '0 0 5px 0', color: '#333' }}>
                                {event.summary}
                            </h4>
                            <p style={{ margin: '0 0 5px 0', color: '#666' }}>
                                <strong>Start:</strong> {new Date(event.start_time).toLocaleString()}
                            </p>
                            <p style={{ margin: '0 0 5px 0', color: '#666' }}>
                                <strong>End:</strong> {new Date(event.end_time).toLocaleString()}
                            </p>
                            {event.description && (
                                <p style={{ margin: '0 0 5px 0', color: '#666' }}>
                                    <strong>Description:</strong> {event.description}
                                </p>
                            )}
                            {event.attendees && event.attendees.length > 0 && (
                                <p style={{ margin: '0', color: '#666' }}>
                                    <strong>Attendees:</strong> {event.attendees.join(', ')}
                                </p>
                            )}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

export default CalendarIntegrationPage; 