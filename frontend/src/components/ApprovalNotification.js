import React, { useState, useEffect } from 'react';
import { useApprovals } from '../context/ApprovalContext';
import { useNavigate } from 'react-router-dom';
import '../styles/ApprovalNotification.css';

const ApprovalNotification = () => {
    const { pendingCount, pendingApprovals } = useApprovals();
    const [lastPendingCount, setLastPendingCount] = useState(0);
    const [showNotification, setShowNotification] = useState(false);
    const [latestApproval, setLatestApproval] = useState(null);
    const navigate = useNavigate();

    // Show notification when new approvals arrive
    useEffect(() => {
        if (pendingCount > lastPendingCount && lastPendingCount > 0) {
            // New approval arrived
            const newest = pendingApprovals[0]; // Assuming newest first
            setLatestApproval(newest);
            setShowNotification(true);

            // Auto-hide after 10 seconds
            const timer = setTimeout(() => {
                setShowNotification(false);
            }, 10000);

            return () => clearTimeout(timer);
        }
        setLastPendingCount(pendingCount);
    }, [pendingCount, lastPendingCount, pendingApprovals]);

    const handleNotificationClick = () => {
        setShowNotification(false);
        navigate('/approvals');
    };

    const dismissNotification = (e) => {
        e.stopPropagation();
        setShowNotification(false);
    };

    if (!showNotification || !latestApproval) {
        return null;
    }

    return (
        <div className="approval-notification" onClick={handleNotificationClick}>
            <div className="notification-header">
                <div className="notification-icon">🔐</div>
                <div className="notification-title">New Approval Request</div>
                <button className="notification-close" onClick={dismissNotification}>
                    ×
                </button>
            </div>
            <div className="notification-content">
                <div className="notification-tool">{latestApproval.tool_name}</div>
                <div className="notification-config">
                    From: {latestApproval.requesting_config_id}
                </div>
                <div className="notification-time">
                    {new Date(latestApproval.created_at).toLocaleTimeString()}
                </div>
            </div>
            <div className="notification-action">
                Click to review →
            </div>
        </div>
    );
};

export default ApprovalNotification;
