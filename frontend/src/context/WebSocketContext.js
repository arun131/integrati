import React, { createContext, useState, useContext, useEffect, useRef, useCallback } from 'react';
import { useAuth } from './AuthContext';

const WebSocketContext = createContext(null);

export const WebSocketProvider = ({ children }) => {
    const { plexusToken, tenantId } = useAuth();
    const [isConnected, setIsConnected] = useState(false);
    const [connectionState, setConnectionState] = useState('disconnected'); // 'disconnected', 'connecting', 'connected', 'error'
    const [lastError, setLastError] = useState(null);
    const [notifications, setNotifications] = useState([]);
    const [unreadCount, setUnreadCount] = useState(0);
    const [approvals, setApprovals] = useState([]);
    const [pendingCount, setPendingCount] = useState(0);

    const wsRef = useRef(null);
    const reconnectTimeoutRef = useRef(null);
    const reconnectAttempts = useRef(0);
    const maxReconnectAttempts = 10;
    const baseReconnectDelay = 1000; // 1 second

    // Event listeners
    const notificationListeners = useRef(new Set());
    const approvalListeners = useRef(new Set());
    const connectionListeners = useRef(new Set());

    const getWebSocketUrl = useCallback(() => {
        if (!tenantId || !plexusToken) return null;

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.hostname;
        // Always use backend port for WebSocket connections
        const port = '8000';
        const baseUrl = `${protocol}//${host}:${port}`;

        return `${baseUrl}/api/events/ws/${tenantId}?token=${encodeURIComponent(plexusToken)}`;
    }, [tenantId, plexusToken]);

    const connect = useCallback(() => {
        const wsUrl = getWebSocketUrl();
        if (!wsUrl) {
            console.log('WebSocket: No URL available, skipping connection');
            return;
        }

        if (wsRef.current?.readyState === WebSocket.OPEN) {
            console.log('WebSocket: Already connected');
            return;
        }

        console.log('WebSocket: Connecting to', wsUrl);
        setConnectionState('connecting');
        setLastError(null);

        try {
            const ws = new WebSocket(wsUrl);
            wsRef.current = ws;

            ws.onopen = () => {
                console.log('WebSocket: Connected successfully');
                setIsConnected(true);
                setConnectionState('connected');
                setLastError(null);
                reconnectAttempts.current = 0;

                // Subscribe to events
                ws.send(JSON.stringify({
                    message_type: 'subscribe',
                    data: {
                        event_types: ['notification', 'approval', 'ping', 'pong']
                    }
                }));

                // Notify connection listeners
                connectionListeners.current.forEach(listener => {
                    try {
                        listener({ type: 'connected', data: { tenantId } });
                    } catch (error) {
                        console.error('Error in connection listener:', error);
                    }
                });
            };

            ws.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    handleMessage(message);
                } catch (error) {
                    console.error('WebSocket: Error parsing message:', error);
                }
            };

            ws.onclose = (event) => {
                console.log('WebSocket: Connection closed', event.code, event.reason);
                console.log('WebSocket: Close details:', {
                    code: event.code,
                    reason: event.reason,
                    wasClean: event.wasClean,
                    target: event.target
                });
                setIsConnected(false);
                setConnectionState('disconnected');
                wsRef.current = null;

                // Notify connection listeners
                connectionListeners.current.forEach(listener => {
                    try {
                        listener({ type: 'disconnected', data: { code: event.code, reason: event.reason } });
                    } catch (error) {
                        console.error('Error in connection listener:', error);
                    }
                });

                // Attempt to reconnect if not a normal closure
                if (event.code !== 1000 && reconnectAttempts.current < maxReconnectAttempts) {
                    scheduleReconnect();
                }
            };

            ws.onerror = (error) => {
                console.error('WebSocket: Connection error:', error);
                console.error('WebSocket: Error details:', {
                    readyState: ws.readyState,
                    url: ws.url,
                    protocol: ws.protocol,
                    extensions: ws.extensions
                });
                setLastError('Connection failed');
                setConnectionState('error');

                // Notify connection listeners
                connectionListeners.current.forEach(listener => {
                    try {
                        listener({ type: 'error', data: { error: 'Connection failed' } });
                    } catch (error) {
                        console.error('Error in connection listener:', error);
                    }
                });
            };

        } catch (error) {
            console.error('WebSocket: Failed to create connection:', error);
            setLastError(`Failed to connect: ${error.message}`);
            setConnectionState('error');
        }
    }, [getWebSocketUrl, tenantId]);

    const disconnect = useCallback(() => {
        console.log('WebSocket: Disconnecting');

        // Clear reconnection timeout
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
            reconnectTimeoutRef.current = null;
        }

        // Close WebSocket connection
        if (wsRef.current) {
            wsRef.current.close(1000, 'User initiated disconnect');
            wsRef.current = null;
        }

        setIsConnected(false);
        setConnectionState('disconnected');
        setLastError(null);
        reconnectAttempts.current = 0;
    }, []);

    const scheduleReconnect = useCallback(() => {
        if (reconnectTimeoutRef.current) return; // Already scheduled

        reconnectAttempts.current += 1;
        const delay = Math.min(
            baseReconnectDelay * Math.pow(2, reconnectAttempts.current - 1),
            30000 // Max 30 seconds
        );

        console.log(`WebSocket: Scheduling reconnect attempt ${reconnectAttempts.current} in ${delay}ms`);

        reconnectTimeoutRef.current = setTimeout(() => {
            reconnectTimeoutRef.current = null;
            if (reconnectAttempts.current <= maxReconnectAttempts) {
                connect();
            } else {
                console.log('WebSocket: Max reconnection attempts reached');
                setConnectionState('error');
                setLastError('Max reconnection attempts reached');
            }
        }, delay);
    }, [connect]);

    const handleMessage = useCallback((message) => {
        console.log('WebSocket: Received message:', message.message_type);

        switch (message.message_type) {
            case 'notification':
                handleNotificationMessage(message.data);
                break;
            case 'approval':
                handleApprovalMessage(message.data);
                break;
            case 'ping':
                handlePingMessage(message.data);
                break;
            case 'pong':
                console.log('WebSocket: Pong received');
                break;
            case 'connection_status':
                console.log('WebSocket: Connection status:', message.data);
                break;
            case 'subscription_confirmed':
                console.log('WebSocket: Subscription confirmed:', message.data);
                break;
            default:
                console.log('WebSocket: Unknown message type:', message.message_type);
        }
    }, []);

    const handleNotificationMessage = useCallback((notificationData) => {
        console.log('WebSocket: Received notification:', notificationData);

        // Update notifications state
        setNotifications(prev => {
            // Check if notification already exists (avoid duplicates)
            const exists = prev.some(n => n.notification_id === notificationData.notification_id);
            if (exists) return prev;

            // Add new notification at the beginning
            return [notificationData, ...prev];
        });

        // Update unread count
        if (!notificationData.is_read) {
            setUnreadCount(prev => prev + 1);
        }

        // Notify listeners
        notificationListeners.current.forEach(listener => {
            try {
                listener({ type: 'new_notification', data: notificationData });
            } catch (error) {
                console.error('Error in notification listener:', error);
            }
        });
    }, []);

    const handleApprovalMessage = useCallback((approvalData) => {
        console.log('WebSocket: Received approval:', approvalData);

        // Update approvals state
        setApprovals(prev => {
            // Check if approval already exists (avoid duplicates)
            const exists = prev.some(a => a.approval_id === approvalData.approval_id);
            if (exists) return prev;

            // Add new approval at the beginning
            return [approvalData, ...prev];
        });

        // Update pending count
        if (approvalData.status === 'pending') {
            setPendingCount(prev => prev + 1);
        }

        // Notify listeners
        approvalListeners.current.forEach(listener => {
            try {
                listener({ type: 'new_approval', data: approvalData });
            } catch (error) {
                console.error('Error in approval listener:', error);
            }
        });
    }, []);

    const handlePingMessage = useCallback((pingData) => {
        // Respond to ping with pong
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({
                message_type: 'pong',
                data: pingData
            }));
        }
    }, []);

    // Send a ping to test connection
    const sendPing = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({
                message_type: 'ping',
                data: { timestamp: new Date().toISOString() }
            }));
        }
    }, []);

    // Event listener management
    const addNotificationListener = useCallback((listener) => {
        notificationListeners.current.add(listener);
        return () => notificationListeners.current.delete(listener);
    }, []);

    const addApprovalListener = useCallback((listener) => {
        approvalListeners.current.add(listener);
        return () => approvalListeners.current.delete(listener);
    }, []);

    const addConnectionListener = useCallback((listener) => {
        connectionListeners.current.add(listener);
        return () => connectionListeners.current.delete(listener);
    }, []);

    // Manual notification/approval state management
    const markNotificationAsRead = useCallback((notificationId) => {
        setNotifications(prev =>
            prev.map(notification =>
                notification.notification_id === notificationId
                    ? { ...notification, is_read: true }
                    : notification
            )
        );
        setUnreadCount(prev => Math.max(0, prev - 1));
    }, []);

    const markAllNotificationsAsRead = useCallback(() => {
        setNotifications(prev =>
            prev.map(notification => ({ ...notification, is_read: true }))
        );
        setUnreadCount(0);
    }, []);

    const updateApprovalStatus = useCallback((approvalId, newStatus) => {
        setApprovals(prev =>
            prev.map(approval =>
                approval.approval_id === approvalId
                    ? { ...approval, status: newStatus }
                    : approval
            )
        );

        if (newStatus !== 'pending') {
            setPendingCount(prev => Math.max(0, prev - 1));
        }
    }, []);

    // Connect/disconnect based on authentication
    useEffect(() => {
        if (plexusToken && tenantId) {
            connect();
        } else {
            disconnect();
        }

        return () => {
            disconnect();
        };
    }, [plexusToken, tenantId, connect, disconnect]);

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            disconnect();
        };
    }, [disconnect]);

    const value = {
        // Connection state
        isConnected,
        connectionState,
        lastError,

        // Data
        notifications,
        unreadCount,
        approvals,
        pendingCount: approvals.filter(a => a.status === 'pending').length,

        // Connection methods
        connect,
        disconnect,
        sendPing,

        // Event listeners
        addNotificationListener,
        addApprovalListener,
        addConnectionListener,

        // State management
        markNotificationAsRead,
        markAllNotificationsAsRead,
        updateApprovalStatus,

        // Manual data updates (for backwards compatibility)
        setNotifications,
        setUnreadCount,
        setApprovals,
        setPendingCount,

        // Connection info
        tenantId,
        reconnectAttempts: reconnectAttempts.current,
        maxReconnectAttempts
    };

    return (
        <WebSocketContext.Provider value={value}>
            {children}
        </WebSocketContext.Provider>
    );
};

export const useWebSocket = () => {
    const context = useContext(WebSocketContext);
    if (!context) {
        throw new Error('useWebSocket must be used within a WebSocketProvider');
    }
    return context;
};
