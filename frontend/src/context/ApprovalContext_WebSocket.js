import React, { createContext, useState, useContext, useEffect, useCallback } from 'react';
import { approvalApi } from '../services/api';
import { useAuth } from './AuthContext';
import { useWebSocket } from './WebSocketContext';

const ApprovalContext = createContext(null);

export const ApprovalProvider = ({ children }) => {
    const { plexusToken } = useAuth();
    const {
        approvals: wsApprovals,
        pendingCount: wsPendingCount,
        isConnected: wsConnected,
        addApprovalListener,
        updateApprovalStatus: wsUpdateApprovalStatus,
        setApprovals: setWsApprovals,
        setPendingCount: setWsPendingCount
    } = useWebSocket();

    const [pendingApprovals, setPendingApprovals] = useState([]);
    const [approvalHistory, setApprovalHistory] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [lastPolled, setLastPolled] = useState(null);

    // Function to load pending approvals
    const loadPendingApprovals = useCallback(async () => {
        if (!plexusToken) return;

        try {
            setLoading(true);
            setError(null);
            const response = await approvalApi.getPendingApprovals();
            const fetchedApprovals = response.pending_approvals || [];

            if (wsConnected) {
                // Sync with WebSocket state - filter only pending ones
                const pendingWsApprovals = wsApprovals.filter(a => a.status === 'pending');
                setPendingApprovals(pendingWsApprovals);

                // Merge fetched approvals with WebSocket approvals to ensure we have complete data
                const mergedApprovals = [...fetchedApprovals];
                wsApprovals.forEach(wsApproval => {
                    if (!mergedApprovals.some(a => a.approval_id === wsApproval.approval_id)) {
                        mergedApprovals.push(wsApproval);
                    }
                });
                setWsApprovals(mergedApprovals);
            } else {
                setPendingApprovals(fetchedApprovals);
            }

            setLastPolled(new Date());
        } catch (err) {
            console.error('Error loading pending approvals:', err);
            setError('Failed to load pending approvals');
        } finally {
            setLoading(false);
        }
    }, [plexusToken, wsConnected, wsApprovals, setWsApprovals]);

    // Function to load approval history
    const loadApprovalHistory = useCallback(async () => {
        if (!plexusToken) return;

        try {
            setLoading(true);
            setError(null);
            const response = await approvalApi.getApprovalHistory();
            setApprovalHistory(response.approval_history || []);
        } catch (err) {
            console.error('Error loading approval history:', err);
            setError('Failed to load approval history');
        } finally {
            setLoading(false);
        }
    }, [plexusToken]);

    // Sync with WebSocket data when connected
    useEffect(() => {
        if (wsConnected) {
            const pendingWsApprovals = wsApprovals.filter(a => a.status === 'pending');
            setPendingApprovals(pendingWsApprovals);
        }
    }, [wsConnected, wsApprovals]);

    // Listen for real-time approval events
    useEffect(() => {
        if (!wsConnected) return;

        const handleApprovalEvent = (event) => {
            if (event.type === 'new_approval') {
                console.log('ApprovalContext: Received real-time approval:', event.data);
                showApprovalToast(event.data);
            }
        };

        const removeListener = addApprovalListener(handleApprovalEvent);
        return removeListener;
    }, [wsConnected, addApprovalListener]);

    const showApprovalToast = (approvalData) => {
        console.log('New approval request:', approvalData.tool_name);

        if ('Notification' in window && Notification.permission === 'granted') {
            new Notification('New Approval Request', {
                body: `${approvalData.tool_name} requires your approval`,
                icon: '/favicon.ico'
            });
        }
    };

    // Fallback polling when WebSocket is not connected
    useEffect(() => {
        if (!wsConnected && plexusToken) {
            console.log('ApprovalContext: WebSocket not connected, using polling fallback');
            loadPendingApprovals();

            // Poll every 30 seconds when WebSocket is not available
            const interval = setInterval(() => {
                loadPendingApprovals();
            }, 30000);

            return () => clearInterval(interval);
        }
    }, [plexusToken, wsConnected, loadPendingApprovals]);

    // Load data when token is available
    useEffect(() => {
        if (plexusToken) {
            loadPendingApprovals();
            loadApprovalHistory();
        }
    }, [plexusToken, loadPendingApprovals, loadApprovalHistory]);

    // Function to approve a request
    const approveRequest = async (approvalId, reason = '') => {
        try {
            setLoading(true);

            // Get current token for execution
            const token = localStorage.getItem('plexus_user_auth_token');
            if (!token) {
                return { success: false, error: 'Authentication token not available' };
            }

            await approvalApi.approveRequest(approvalId, reason, token);

            // Update states
            if (wsConnected) {
                wsUpdateApprovalStatus(approvalId, 'approved');
            } else {
                setPendingApprovals(prev => prev.filter(approval => approval.approval_id !== approvalId));
            }

            await loadApprovalHistory();

            return { success: true };
        } catch (err) {
            console.error('Error approving request:', err);
            return { success: false, error: err.message || 'Failed to approve request' };
        } finally {
            setLoading(false);
        }
    };

    // Function to deny a request
    const denyRequest = async (approvalId, reason = '') => {
        try {
            setLoading(true);
            await approvalApi.denyRequest(approvalId, reason);

            // Update states
            if (wsConnected) {
                wsUpdateApprovalStatus(approvalId, 'denied');
            } else {
                setPendingApprovals(prev => prev.filter(approval => approval.approval_id !== approvalId));
            }

            await loadApprovalHistory();

            return { success: true };
        } catch (err) {
            console.error('Error denying request:', err);
            return { success: false, error: err.message || 'Failed to deny request' };
        } finally {
            setLoading(false);
        }
    };

    const value = {
        pendingApprovals: wsConnected ? wsApprovals.filter(a => a.status === 'pending') : pendingApprovals,
        approvalHistory,
        loading,
        error,
        loadPendingApprovals,
        loadApprovalHistory,
        approveRequest,
        denyRequest,
        pendingCount: wsConnected ? wsApprovals.filter(a => a.status === 'pending').length : pendingApprovals.length,

        // Additional WebSocket-specific properties
        isRealTime: wsConnected,
        lastPolled,
        connectionState: wsConnected ? 'connected' : 'polling',
        allApprovals: wsConnected ? wsApprovals : [...pendingApprovals, ...approvalHistory]
    };

    return (
        <ApprovalContext.Provider value={value}>
            {children}
        </ApprovalContext.Provider>
    );
};

export const useApprovals = () => {
    const context = useContext(ApprovalContext);
    if (!context) {
        throw new Error('useApprovals must be used within an ApprovalProvider');
    }
    return context;
};
