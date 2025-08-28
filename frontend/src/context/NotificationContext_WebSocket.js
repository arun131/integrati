import React, { createContext, useState, useContext, useEffect, useCallback } from 'react';
import { notificationApi } from '../services/api';
import { useAuth } from './AuthContext';
import { useWebSocket } from './WebSocketContext';

const NotificationContext = createContext(null);

export const NotificationProvider = ({ children }) => {
    const { plexusToken, tenantId } = useAuth();
    const {
        notifications: wsNotifications,
        unreadCount: wsUnreadCount,
        isConnected: wsConnected,
        addNotificationListener,
        markNotificationAsRead: wsMarkAsRead,
        markAllNotificationsAsRead: wsMarkAllAsRead,
        setNotifications: setWsNotifications,
        setUnreadCount: setWsUnreadCount
    } = useWebSocket();

    const [notifications, setNotifications] = useState([]);
    const [unreadCount, setUnreadCount] = useState(0);
    const [loading, setLoading] = useState(false);
    const [lastPolled, setLastPolled] = useState(null);

    // Fallback polling when WebSocket is not connected
    useEffect(() => {
        if (!wsConnected && plexusToken) {
            console.log('NotificationContext: WebSocket not connected, using polling fallback');
            loadNotifications();
            loadUnreadCount();

            // Poll every 10 minutes when WebSocket is not available
            const interval = setInterval(() => {
                loadUnreadCount();
                loadNotifications();
            }, 600000);

            return () => clearInterval(interval);
        } else if (wsConnected) {
            console.log('NotificationContext: WebSocket connected, stopping fallback polling');
        }
    }, [plexusToken, wsConnected]);

    // Initial data load only when WebSocket is not connected
    useEffect(() => {
        if (!wsConnected && plexusToken) {
            console.log('NotificationContext: Initial data load (WebSocket not connected)');
            loadNotifications();
            loadUnreadCount();
        }
    }, [plexusToken, wsConnected]);

    // Sync with WebSocket data when connected
    useEffect(() => {
        if (wsConnected) {
            setNotifications(wsNotifications);
            setUnreadCount(wsUnreadCount);
        }
    }, [wsConnected, wsNotifications, wsUnreadCount]);

    // Listen for real-time notification events
    useEffect(() => {
        if (!wsConnected) return;

        const handleNotificationEvent = (event) => {
            if (event.type === 'new_notification') {
                console.log('NotificationContext: Received real-time notification:', event.data);
                // WebSocket context already handles the state update
                // We can add any additional UI-specific logic here
                showNotificationToast(event.data);
            }
        };

        const removeListener = addNotificationListener(handleNotificationEvent);
        return removeListener;
    }, [wsConnected, addNotificationListener]);

    const showNotificationToast = (notificationData) => {
        // You can integrate with a toast library here
        console.log('New notification:', notificationData.notification_text);

        // For now, we'll just log it. You could integrate with react-toastify or similar
        if ('Notification' in window && Notification.permission === 'granted') {
            new Notification('New Notification', {
                body: notificationData.notification_text,
                icon: '/favicon.ico'
            });
        }
    };

    const loadNotifications = async (includeRead = false) => {
        if (!plexusToken) return;

        // Don't make API calls if WebSocket is connected
        if (wsConnected) {
            console.log('NotificationContext: WebSocket connected, skipping API call');
            return;
        }

        try {
            setLoading(true);
            const response = await notificationApi.getNotifications(20, includeRead);
            const fetchedNotifications = response.notifications || [];
            const fetchedUnreadCount = response.unread_count || 0;

            // Use local state since WebSocket is not connected
            setNotifications(fetchedNotifications);
            setUnreadCount(fetchedUnreadCount);

            setLastPolled(new Date());
        } catch (error) {
            console.error('Error loading notifications:', error);
        } finally {
            setLoading(false);
        }
    };

    const loadUnreadCount = async () => {
        if (!plexusToken) return;

        // Don't make API calls if WebSocket is connected
        if (wsConnected) {
            console.log('NotificationContext: WebSocket connected, skipping API call');
            return;
        }

        try {
            const response = await notificationApi.getNotificationCount();
            const fetchedUnreadCount = response.unread_count || 0;

            setUnreadCount(fetchedUnreadCount);
        } catch (error) {
            console.error('Error loading notification count:', error);
        }
    };

    const markAsRead = async (notificationId) => {
        try {
            await notificationApi.markNotificationAsRead(notificationId);

            if (wsConnected) {
                // Update WebSocket state
                wsMarkAsRead(notificationId);
            } else {
                // Update local state
                setNotifications(prev =>
                    prev.map(notification =>
                        notification.notification_id === notificationId
                            ? { ...notification, is_read: true }
                            : notification
                    )
                );
                setUnreadCount(prev => Math.max(0, prev - 1));
            }
        } catch (error) {
            console.error('Error marking notification as read:', error);
        }
    };

    const markAllAsRead = async () => {
        try {
            await notificationApi.markAllNotificationsAsRead();

            if (wsConnected) {
                // Update WebSocket state
                wsMarkAllAsRead();
            } else {
                // Update local state
                setNotifications(prev =>
                    prev.map(notification => ({ ...notification, is_read: true }))
                );
                setUnreadCount(0);
            }
        } catch (error) {
            console.error('Error marking all notifications as read:', error);
        }
    };

    const refreshNotifications = useCallback(() => {
        loadNotifications();
        loadUnreadCount();
    }, []);

    // Request notification permission on mount
    useEffect(() => {
        if ('Notification' in window && Notification.permission === 'default') {
            Notification.requestPermission();
        }
    }, []);

    const value = {
        notifications: wsConnected ? wsNotifications : notifications,
        unreadCount: wsConnected ? wsUnreadCount : unreadCount,
        loading,
        loadNotifications,
        loadUnreadCount,
        markAsRead,
        markAllAsRead,
        refreshNotifications,

        // Additional WebSocket-specific properties
        isRealTime: wsConnected,
        lastPolled,
        connectionState: wsConnected ? 'connected' : 'polling'
    };

    return (
        <NotificationContext.Provider value={value}>
            {children}
        </NotificationContext.Provider>
    );
};

export const useNotifications = () => {
    const context = useContext(NotificationContext);
    if (!context) {
        throw new Error('useNotifications must be used within a NotificationProvider');
    }
    return context;
};
