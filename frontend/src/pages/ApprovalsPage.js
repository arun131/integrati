import React, { useState } from 'react';
import { useApprovals } from '../context/ApprovalContext_WebSocket';
import '../styles/ApprovalsPage.css';

const ApprovalsPage = () => {
    const {
        pendingApprovals,
        approvalHistory,
        loading,
        error,
        approveRequest,
        denyRequest,
        loadPendingApprovals
    } = useApprovals();

    const [activeTab, setActiveTab] = useState('pending');
    const [selectedApproval, setSelectedApproval] = useState(null);
    const [reasonModal, setReasonModal] = useState({ show: false, type: '', approvalId: '' });
    const [reason, setReason] = useState('');
    const [processing, setProcessing] = useState(false);

    const formatDate = (dateString) => {
        return new Date(dateString).toLocaleString();
    };

    const formatToolParams = (params) => {
        try {
            const parsed = typeof params === 'string' ? JSON.parse(params) : params;
            return Object.entries(parsed).map(([key, value]) => (
                <div key={key} className="param-item">
                    <strong>{key}:</strong> {JSON.stringify(value)}
                </div>
            ));
        } catch (e) {
            return <div className="param-item">Invalid parameters format</div>;
        }
    };

    const handleApprovalAction = async (approvalId, action) => {
        setReasonModal({ show: true, type: action, approvalId });
    };

    const confirmAction = async () => {
        setProcessing(true);
        const { type, approvalId } = reasonModal;

        let result;
        if (type === 'approve') {
            result = await approveRequest(approvalId, reason);
        } else {
            result = await denyRequest(approvalId, reason);
        }

        if (result.success) {
            setReasonModal({ show: false, type: '', approvalId: '' });
            setReason('');
            await loadPendingApprovals();
        } else {
            alert(`Failed to ${type} request: ${result.error}`);
        }
        setProcessing(false);
    };

    const closeModal = () => {
        setReasonModal({ show: false, type: '', approvalId: '' });
        setReason('');
    };

    const getStatusBadge = (status) => {
        const statusClass = {
            'pending': 'status-pending',
            'approved': 'status-approved',
            'denied': 'status-denied',
            'executed': 'status-executed'
        }[status] || 'status-pending';

        return <span className={`status-badge ${statusClass}`}>{status.toUpperCase()}</span>;
    };

    if (loading && pendingApprovals.length === 0 && approvalHistory.length === 0) {
        return (
            <div className="approvals-page">
                <div className="loading-container">
                    <div className="loading-spinner"></div>
                    <p>Loading approvals...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="approvals-page">
            <div className="approvals-header">
                <h1>Tool Approvals</h1>
                <p>Manage background agent tool execution requests</p>
            </div>

            {error && (
                <div className="error-message">
                    <strong>Error:</strong> {error}
                </div>
            )}

            <div className="approval-tabs">
                <button
                    className={`tab ${activeTab === 'pending' ? 'active' : ''}`}
                    onClick={() => setActiveTab('pending')}
                >
                    Pending ({pendingApprovals.length})
                </button>
                <button
                    className={`tab ${activeTab === 'history' ? 'active' : ''}`}
                    onClick={() => setActiveTab('history')}
                >
                    History ({approvalHistory.length})
                </button>
            </div>

            <div className="approval-content">
                {activeTab === 'pending' && (
                    <div className="pending-approvals">
                        {pendingApprovals.length === 0 ? (
                            <div className="empty-state">
                                <h3>No Pending Approvals</h3>
                                <p>All background agent requests have been processed!</p>
                            </div>
                        ) : (
                            <div className="approval-list">
                                {pendingApprovals.map((approval) => (
                                    <div key={approval.approval_id} className="approval-card pending">
                                        <div className="approval-header">
                                            <div className="tool-info">
                                                <h3>{approval.tool_name}</h3>
                                                <span className="config-badge">
                                                    {approval.requesting_config_id}
                                                </span>
                                            </div>
                                            <div className="approval-actions">
                                                <button
                                                    className="btn btn-approve"
                                                    onClick={() => handleApprovalAction(approval.approval_id, 'approve')}
                                                    disabled={processing}
                                                >
                                                    Approve
                                                </button>
                                                <button
                                                    className="btn btn-deny"
                                                    onClick={() => handleApprovalAction(approval.approval_id, 'deny')}
                                                    disabled={processing}
                                                >
                                                    Deny
                                                </button>
                                            </div>
                                        </div>

                                        <div className="approval-details">
                                            <div className="detail-row">
                                                <strong>Requested:</strong>
                                                <span>{formatDate(approval.created_at)}</span>
                                            </div>

                                            {approval.tool_context && (
                                                <div className="detail-row">
                                                    <strong>Context:</strong>
                                                    <span>{approval.tool_context}</span>
                                                </div>
                                            )}

                                            <div className="tool-params">
                                                <strong>Parameters:</strong>
                                                <div className="params-list">
                                                    {formatToolParams(approval.tool_params)}
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {activeTab === 'history' && (
                    <div className="approval-history">
                        {approvalHistory.length === 0 ? (
                            <div className="empty-state">
                                <h3>No Approval History</h3>
                                <p>No background agent requests have been processed yet.</p>
                            </div>
                        ) : (
                            <div className="approval-list">
                                {approvalHistory.map((approval) => (
                                    <div key={approval.approval_id} className={`approval-card ${approval.status}`}>
                                        <div className="approval-header">
                                            <div className="tool-info">
                                                <h3>{approval.tool_name}</h3>
                                                <span className="config-badge">
                                                    {approval.requesting_config_id}
                                                </span>
                                            </div>
                                            <div className="status-info">
                                                {getStatusBadge(approval.status)}
                                            </div>
                                        </div>

                                        <div className="approval-details">
                                            <div className="detail-row">
                                                <strong>Requested:</strong>
                                                <span>{formatDate(approval.created_at)}</span>
                                            </div>

                                            <div className="detail-row">
                                                <strong>Responded:</strong>
                                                <span>{formatDate(approval.responded_at)}</span>
                                            </div>

                                            {approval.response_reason && (
                                                <div className="detail-row">
                                                    <strong>Reason:</strong>
                                                    <span>{approval.response_reason}</span>
                                                </div>
                                            )}

                                            {approval.tool_context && (
                                                <div className="detail-row">
                                                    <strong>Context:</strong>
                                                    <span>{approval.tool_context}</span>
                                                </div>
                                            )}

                                            <div className="tool-params">
                                                <strong>Parameters:</strong>
                                                <div className="params-list">
                                                    {formatToolParams(approval.tool_params)}
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* Reason Modal */}
            {reasonModal.show && (
                <div className="modal-overlay">
                    <div className="modal-content">
                        <div className="modal-header">
                            <h3>
                                {reasonModal.type === 'approve' ? 'Approve' : 'Deny'} Request
                            </h3>
                            <button className="modal-close" onClick={closeModal}>×</button>
                        </div>

                        <div className="modal-body">
                            <label htmlFor="reason">
                                Reason (optional):
                            </label>
                            <textarea
                                id="reason"
                                value={reason}
                                onChange={(e) => setReason(e.target.value)}
                                placeholder={`Enter reason for ${reasonModal.type}...`}
                                rows="3"
                            />
                        </div>

                        <div className="modal-footer">
                            <button
                                className="btn btn-secondary"
                                onClick={closeModal}
                                disabled={processing}
                            >
                                Cancel
                            </button>
                            <button
                                className={`btn ${reasonModal.type === 'approve' ? 'btn-approve' : 'btn-deny'}`}
                                onClick={confirmAction}
                                disabled={processing}
                            >
                                {processing ? 'Processing...' :
                                 reasonModal.type === 'approve' ? 'Approve' : 'Deny'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default ApprovalsPage;
