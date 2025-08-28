import React, { createContext, useState, useContext, useEffect, useCallback } from 'react';
import { approvalApi } from '../services/api';
import { useAuth } from './AuthContext';

const ApprovalContext = createContext(null);

export const ApprovalProvider = ({ children }) => {
    const [pendingApprovals, setPendingApprovals] = useState([]);
    const [approvalHistory, setApprovalHistory] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const { plexusToken } = useAuth();

    // Function to load pending approvals
    const loadPendingApprovals = useCallback(async () => {
        if (!plexusToken) return;

        try {
            setLoading(true);
            setError(null);
            const response = await approvalApi.getPendingApprovals();
            setPendingApprovals(response.pending_approvals || []);
        } catch (err) {
            console.error('Error loading pending approvals:', err);
            setError('Failed to load pending approvals');
        } finally {
            setLoading(false);
        }
    }, [plexusToken]);

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

            // Remove from pending and reload data
            setPendingApprovals(prev => prev.filter(approval => approval.approval_id !== approvalId));
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

            // Remove from pending and reload data
            setPendingApprovals(prev => prev.filter(approval => approval.approval_id !== approvalId));
            await loadApprovalHistory();

            return { success: true };
        } catch (err) {
            console.error('Error denying request:', err);
            return { success: false, error: err.message || 'Failed to deny request' };
        } finally {
            setLoading(false);
        }
    };

    // Load data when token is available
    useEffect(() => {
        if (plexusToken) {
            loadPendingApprovals();
            loadApprovalHistory();
        }
    }, [plexusToken, loadPendingApprovals, loadApprovalHistory]);

    // Set up polling for new approvals (every 10 minutes when user is active)
    useEffect(() => {
        if (!plexusToken) return;

        const interval = setInterval(() => {
            loadPendingApprovals();
        }, 600000); // Poll every 10 minutes

        return () => clearInterval(interval);
    }, [plexusToken, loadPendingApprovals]);

    const value = {
        pendingApprovals,
        approvalHistory,
        loading,
        error,
        loadPendingApprovals,
        loadApprovalHistory,
        approveRequest,
        denyRequest,
        pendingCount: pendingApprovals.length
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
