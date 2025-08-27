import React, { createContext, useState, useContext, useEffect } from 'react';
import { notificationApi } from '../services/api';
import { useAuth } from './AuthContext';

const NotificationContext = createContext(null);

export const NotificationProvider = ({ children }) => {
    const { plexusToken, tenantId } = useAuth();
    const [notifications, setNotifications] = useState([]);
    const [unreadCount, setUnreadCount] = useState(0);
    const [loading, setLoading] = useState(false);

    // Load notifications when component mounts or when authentication changes
    useEffect(() => {
        if (plexusToken) {
            loadNotifications();
            loadUnreadCount();

            // Poll for new notifications and count every 10 seconds
            const interval = setInterval(() => {
                loadUnreadCount();
                loadNotifications();
            }, 10000);

            return () => clearInterval(interval);
        }
    }, [plexusToken]);

    const loadNotifications = async (includeRead = false) => {
        if (!plexusToken) return;

        try {
            setLoading(true);
            const response = await notificationApi.getNotifications(20, includeRead);
            setNotifications(response.notifications || []);
            setUnreadCount(response.unread_count || 0);
        } catch (error) {
            console.error('Error loading notifications:', error);
        } finally {
            setLoading(false);
        }
    };

    const loadUnreadCount = async () => {
        if (!plexusToken) return;

        try {
            const response = await notificationApi.getNotificationCount();
            setUnreadCount(response.unread_count || 0);
        } catch (error) {
            console.error('Error loading notification count:', error);
        }
    };

    const markAsRead = async (notificationId) => {
        try {
            await notificationApi.markNotificationAsRead(notificationId);

            // Update local state
            setNotifications(prev =>
                prev.map(notification =>
                    notification.notification_id === notificationId
                        ? { ...notification, is_read: true }
                        : notification
                )
            );

            // Update unread count
            setUnreadCount(prev => Math.max(0, prev - 1));
        } catch (error) {
            console.error('Error marking notification as read:', error);
        }
    };

    const markAllAsRead = async () => {
        try {
            await notificationApi.markAllNotificationsAsRead();

            // Update local state
            setNotifications(prev =>
                prev.map(notification => ({ ...notification, is_read: true }))
            );
            setUnreadCount(0);
        } catch (error) {
            console.error('Error marking all notifications as read:', error);
        }
    };

    const value = {
        notifications,
        unreadCount,
        loading,
        loadNotifications,
        loadUnreadCount,
        markAsRead,
        markAllAsRead,
        refreshNotifications: () => {
            loadNotifications();
            loadUnreadCount();
        }
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
