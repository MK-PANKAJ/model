import { useState } from 'react';
import API from '../config';

export default function UpdateStatusModal({ caseId, currentStatus, companyName, onClose, onSuccess }) {
    const [selectedStatus, setSelectedStatus] = useState('');
    const [reason, setReason] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    // Valid transitions based on current status
    const getValidTransitions = (current) => {
        const transitions = {
            'PENDING': ['IN_PROGRESS', 'CLOSED'],
            'IN_PROGRESS': ['UNDER_REVIEW', 'RESOLVED', 'CLOSED', 'ESCALATED'],
            'UNDER_REVIEW': ['IN_PROGRESS', 'RESOLVED', 'ESCALATED'],
            'RESOLVED': ['CLOSED'],
            'ESCALATED': ['UNDER_REVIEW', 'CLOSED'],
            'CLOSED': []
        };
        return transitions[current] || [];
    };

    const validStatuses = getValidTransitions(currentStatus);

    const handleUpdate = async () => {
        if (!selectedStatus) {
            setError('Please select a new status');
            return;
        }

        if (selectedStatus === 'CLOSED' && !reason.trim()) {
            setError('Please provide a reason for closing the case');
            return;
        }

        setLoading(true);
        setError('');

        try {
            const token = localStorage.getItem('token');
            const response = await fetch(
                API.UPDATE_STATUS(caseId),
                {
                    method: 'PATCH',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`
                    },
                    body: JSON.stringify({
                        new_status: selectedStatus,
                        reason: reason.trim() || null
                    })
                }
            );

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.detail || 'Failed to update status');
            }

            const data = await response.json();
            setTimeout(() => {
                onSuccess();
                onClose();
            }, 1000);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const getStatusDescription = (status) => {
        const descriptions = {
            'IN_PROGRESS': 'Agent actively working on this case',
            'UNDER_REVIEW': 'Needs supervisor/manager review',
            'RESOLVED': 'Successfully resolved (payment received or settled)',
            'CLOSED': 'Case finalized and archived',
            'ESCALATED': 'Escalated due to compliance or other issues'
        };
        return descriptions[status] || '';
    };

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-white rounded-xl shadow-2xl p-6 w-full max-w-md">
                <div className="flex justify-between items-center mb-4">
                    <div>
                        <h2 className="text-2xl font-bold text-gray-800">Update Status</h2>
                        <p className="text-sm text-gray-500">{companyName}</p>
                    </div>
                    <button
                        onClick={onClose}
                        className="text-gray-400 hover:text-gray-600 text-2xl"
                    >
                        ×
                    </button>
                </div>

                {error && (
                    <div className="bg-red-50 text-red-600 p-3 rounded mb-4 text-sm">
                        {error}
                    </div>
                )}

                <div className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Current Status: <span className="font-bold text-blue-600">{currentStatus.replace('_', ' ')}</span>
                        </label>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            New Status
                        </label>
                        <select
                            className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                            value={selectedStatus}
                            onChange={(e) => setSelectedStatus(e.target.value)}
                            disabled={loading || validStatuses.length === 0}
                        >
                            <option value="">-- Select Status --</option>
                            {validStatuses.map((status) => (
                                <option key={status} value={status}>
                                    {status.replace('_', ' ')}
                                </option>
                            ))}
                        </select>
                        {selectedStatus && (
                            <p className="text-xs text-gray-500 mt-1">
                                {getStatusDescription(selectedStatus)}
                            </p>
                        )}
                        {validStatuses.length === 0 && (
                            <p className="text-xs text-gray-500 mt-1">
                                No valid transitions available from {currentStatus}
                            </p>
                        )}
                    </div>

                    {selectedStatus && (
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Reason {selectedStatus === 'CLOSED' && <span className="text-red-500">*</span>}
                            </label>
                            <textarea
                                className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none"
                                rows="3"
                                value={reason}
                                onChange={(e) => setReason(e.target.value)}
                                placeholder={selectedStatus === 'CLOSED' ? 'Required: Why is this case being closed?' : 'Optional: Additional context for this change'}
                                disabled={loading}
                            />
                        </div>
                    )}

                    <div className="flex gap-3 pt-2">
                        <button
                            type="button"
                            onClick={onClose}
                            className="flex-1 bg-gray-100 text-gray-700 py-2 px-4 rounded-lg hover:bg-gray-200 transition"
                            disabled={loading}
                        >
                            Cancel
                        </button>
                        <button
                            onClick={handleUpdate}
                            disabled={loading || !selectedStatus}
                            className="flex-1 bg-indigo-600 text-white py-2 px-4 rounded-lg hover:bg-indigo-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {loading ? 'Updating...' : 'Update Status'}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
