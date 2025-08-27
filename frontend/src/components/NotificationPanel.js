import React, { useState } from 'react';
import { useNotifications } from '../context/NotificationContext_WebSocket';

const NotificationPanel = () => {
    const {
        notifications,
        unreadCount,
        loading,
        markAsRead,
        markAllAsRead,
        loadNotifications
    } = useNotifications();

    const [showAll, setShowAll] = useState(false);

    const handleToggleShowAll = () => {
        const newShowAll = !showAll;
        setShowAll(newShowAll);
        loadNotifications(newShowAll); // Load with includeRead parameter
    };

    const formatTimestamp = (timestamp) => {
        const date = new Date(timestamp);
        const now = new Date();
        const diffTime = Math.abs(now - date);
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

        if (diffDays === 1) {
            return 'Today';
        } else if (diffDays === 2) {
            return 'Yesterday';
        } else if (diffDays <= 7) {
            return `${diffDays - 1} days ago`;
        } else {
            return date.toLocaleDateString();
        }
    };

    const getIntegrationIcon = (integrationType) => {
        switch (integrationType) {
            case 'gmail':
                return '📧';
            case 'calendar':
                return '📅';
            default:
                return '🔔';
        }
    };

    const getPriorityColor = (priority) => {
        switch (priority) {
            case 'high':
                return '#dc3545';
            case 'normal':
                return '#007bff';
            case 'low':
                return '#6c757d';
            default:
                return '#007bff';
        }
    };

    if (loading && notifications.length === 0) {
        return (
            <div style={{
                padding: '20px',
                textAlign: 'center',
                color: '#666'
            }}>
                Loading notifications...
            </div>
        );
    }

    return (
        <div style={{
            backgroundColor: 'white',
            border: '1px solid #dee2e6',
            borderRadius: '8px',
            marginBottom: '30px'
        }}>
            {/* Header */}
            <div style={{
                padding: '20px',
                borderBottom: '1px solid #dee2e6',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <h3 style={{ margin: '0', color: '#333' }}>
                        🔔 Notifications
                    </h3>
                    {unreadCount > 0 && (
                        <span style={{
                            backgroundColor: '#dc3545',
                            color: 'white',
                            borderRadius: '50%',
                            padding: '2px 8px',
                            fontSize: '12px',
                            fontWeight: 'bold',
                            minWidth: '20px',
                            textAlign: 'center'
                        }}>
                            {unreadCount}
                        </span>
                    )}
                </div>

                <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                    <label style={{ fontSize: '14px', color: '#666', display: 'flex', alignItems: 'center', gap: '5px' }}>
                        <input
                            type="checkbox"
                            checked={showAll}
                            onChange={handleToggleShowAll}
                        />
                        Show read
                    </label>

                    {unreadCount > 0 && (
                        <button
                            onClick={markAllAsRead}
                            style={{
                                padding: '5px 10px',
                                backgroundColor: '#28a745',
                                color: 'white',
                                border: 'none',
                                borderRadius: '4px',
                                cursor: 'pointer',
                                fontSize: '12px'
                            }}
                        >
                            Mark all read
                        </button>
                    )}
                </div>
            </div>

            {/* Notifications List */}
            <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
                {notifications.length === 0 ? (
                    <div style={{
                        padding: '40px',
                        textAlign: 'center',
                        color: '#666'
                    }}>
                        <div style={{ fontSize: '48px', marginBottom: '10px' }}>🔔</div>
                        <div>No notifications yet</div>
                        <div style={{ fontSize: '14px', marginTop: '5px' }}>
                            Notifications from your background agents will appear here
                        </div>
                    </div>
                ) : (
                    notifications.map((notification) => (
                        <div
                            key={notification.notification_id}
                            style={{
                                padding: '15px 20px',
                                borderBottom: '1px solid #f0f0f0',
                                backgroundColor: notification.is_read ? '#fff' : '#f8f9fa',
                                cursor: notification.is_read ? 'default' : 'pointer',
                                transition: 'background-color 0.2s ease'
                            }}
                            onClick={() => !notification.is_read && markAsRead(notification.notification_id)}
                        >
                            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
                                {/* Integration Icon */}
                                <div style={{
                                    fontSize: '20px',
                                    minWidth: '24px',
                                    display: 'flex',
                                    alignItems: 'center',
                                    marginTop: '2px'
                                }}>
                                    {getIntegrationIcon(notification.integration_type)}
                                </div>

                                {/* Notification Content */}
                                <div style={{ flex: 1, minWidth: 0 }}>
                                    <div style={{
                                        fontSize: '14px',
                                        color: '#333',
                                        lineHeight: '1.4',
                                        marginBottom: '8px'
                                    }}>
                                        {notification.notification_text}
                                    </div>

                                    <div style={{
                                        display: 'flex',
                                        justifyContent: 'space-between',
                                        alignItems: 'center',
                                        fontSize: '12px',
                                        color: '#666'
                                    }}>
                                        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                                            <span>
                                                {notification.integration_type.charAt(0).toUpperCase() + notification.integration_type.slice(1)} Agent
                                            </span>
                                            <span style={{
                                                width: '4px',
                                                height: '4px',
                                                borderRadius: '50%',
                                                backgroundColor: getPriorityColor(notification.priority),
                                                display: 'inline-block'
                                            }}></span>
                                            <span style={{ color: getPriorityColor(notification.priority) }}>
                                                {notification.priority}
                                            </span>
                                        </div>

                                        <span>
                                            {formatTimestamp(notification.timestamp)}
                                        </span>
                                    </div>
                                </div>

                                {/* Unread Indicator */}
                                {!notification.is_read && (
                                    <div style={{
                                        width: '8px',
                                        height: '8px',
                                        borderRadius: '50%',
                                        backgroundColor: '#007bff',
                                        marginTop: '6px'
                                    }}></div>
                                )}
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
};

export default NotificationPanel;
