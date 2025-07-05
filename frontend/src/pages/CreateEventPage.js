import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';

function CreateEventPage() {
    const navigate = useNavigate();
    const [summary, setSummary] = useState('');
    const [description, setDescription] = useState('');
    const [startTime, setStartTime] = useState('');
    const [endTime, setEndTime] = useState('');
    const [attendees, setAttendees] = useState('');
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
                summary: summary,
                description: description,
                start_time: startTime,
                end_time: endTime,
                attendees: attendees ? attendees.split(',').map(email => email.trim()) : []
            };
            
            await api.post('/integrations/calendar/api/events', payload);
            setSuccess(true);
            setSummary('');
            setDescription('');
            setStartTime('');
            setEndTime('');
            setAttendees('');
        } catch (err) {
            setError('Failed to create event. Please check your inputs and try again.');
            console.error('Create event error:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleBack = () => {
        navigate('/dashboard');
    };

    return (
        <div style={{ padding: '20px', maxWidth: '600px', margin: 'auto', fontFamily: 'Arial, sans-serif' }}>
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
                <h2 style={{ color: '#333', margin: '0' }}>Create New Event</h2>
            </div>

            <form onSubmit={handleSubmit} style={{ 
                border: '1px solid #ddd', 
                padding: '20px', 
                borderRadius: '8px', 
                boxShadow: '0 2px 4px rgba(0,0,0,0.1)' 
            }}>
                <div style={{ marginBottom: '15px' }}>
                    <label htmlFor="summary" style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Event Title:</label>
                    <input
                        type="text"
                        id="summary"
                        value={summary}
                        onChange={(e) => setSummary(e.target.value)}
                        required
                        style={{ width: 'calc(100% - 22px)', padding: '10px', border: '1px solid #ccc', borderRadius: '4px' }}
                    />
                </div>

                <div style={{ marginBottom: '15px' }}>
                    <label htmlFor="description" style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Description:</label>
                    <textarea
                        id="description"
                        value={description}
                        onChange={(e) => setDescription(e.target.value)}
                        rows="4"
                        style={{ width: 'calc(100% - 22px)', padding: '10px', border: '1px solid #ccc', borderRadius: '4px', resize: 'vertical' }}
                    ></textarea>
                </div>

                <div style={{ marginBottom: '15px' }}>
                    <label htmlFor="startTime" style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Start Time:</label>
                    <input
                        type="datetime-local"
                        id="startTime"
                        value={startTime}
                        onChange={(e) => setStartTime(e.target.value)}
                        required
                        style={{ width: 'calc(100% - 22px)', padding: '10px', border: '1px solid #ccc', borderRadius: '4px' }}
                    />
                </div>

                <div style={{ marginBottom: '15px' }}>
                    <label htmlFor="endTime" style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>End Time:</label>
                    <input
                        type="datetime-local"
                        id="endTime"
                        value={endTime}
                        onChange={(e) => setEndTime(e.target.value)}
                        required
                        style={{ width: 'calc(100% - 22px)', padding: '10px', border: '1px solid #ccc', borderRadius: '4px' }}
                    />
                </div>

                <div style={{ marginBottom: '15px' }}>
                    <label htmlFor="attendees" style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Attendees (comma-separated emails):</label>
                    <input
                        type="text"
                        id="attendees"
                        value={attendees}
                        onChange={(e) => setAttendees(e.target.value)}
                        placeholder="email1@example.com, email2@example.com"
                        style={{ width: 'calc(100% - 22px)', padding: '10px', border: '1px solid #ccc', borderRadius: '4px' }}
                    />
                </div>

                {error && <p style={{ color: '#dc3545', marginBottom: '10px' }}>Error: {error}</p>}
                {success && <p style={{ color: '#28a745', marginBottom: '10px' }}>Event created successfully!</p>}

                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <button
                        type="submit"
                        disabled={loading}
                        style={{ 
                            padding: '10px 20px', 
                            backgroundColor: '#34a853', 
                            color: 'white', 
                            border: 'none', 
                            borderRadius: '5px', 
                            cursor: 'pointer' 
                        }}
                    >
                        {loading ? 'Creating...' : 'Create Event'}
                    </button>
                    <button
                        type="button"
                        onClick={handleBack}
                        style={{ 
                            padding: '10px 20px', 
                            backgroundColor: '#6c757d', 
                            color: 'white', 
                            border: 'none', 
                            borderRadius: '5px', 
                            cursor: 'pointer' 
                        }}
                    >
                        Cancel
                    </button>
                </div>
            </form>
        </div>
    );
}

export default CreateEventPage; 