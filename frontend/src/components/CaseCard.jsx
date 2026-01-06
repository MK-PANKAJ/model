import React, { useState } from 'react';
import LogCallModal from './LogCallModal';
import StatusBadge from './StatusBadge';
import UpdateStatusModal from './UpdateStatusModal';
import { API } from '../config';

// The "Smart Card" that displays the ODE Score and Suggested Action
const CaseCard = ({ caseData, onPay, onLogCall, onCall }) => {
    const [showLogModal, setShowLogModal] = useState(false);
    const [showHistory, setShowHistory] = useState(false);
    const [showStatusModal, setShowStatusModal] = useState(false);
    const [editingPhone, setEditingPhone] = useState(false);
    const [newPhone, setNewPhone] = useState('');

    // Destructure data from the RISKON Engine
    const { case_id, companyName, phone: initialPhone, amount, pScore, suggestedAction, riskLevel, violationTag, history = [], status = 'PENDING' } = caseData;
    const [phone, setPhone] = useState(initialPhone);

    const handleUpdatePhone = async () => {
        try {
            const token = localStorage.getItem('token');
            const response = await fetch(API.UPDATE_CONTACT(case_id), {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ phone: newPhone })
            });

            if (response.ok) {
                setPhone(newPhone);
                setEditingPhone(false);
            }
        } catch (err) {
            console.error("Failed to update phone", err);
        }
    };

    // Dynamic Styling based on Recovery Probability (ODE Score)
    const getPriorityColor = (score) => {
        if (score > 0.8) return "bg-green-50 border-l-4 border-green-500"; // High P(Pay)
        if (score > 0.5) return "bg-yellow-50 border-l-4 border-yellow-500";
        return "bg-gray-50 border-l-4 border-gray-400"; // Low P(Pay) - Automate
    };

    // Format Action Text
    const formatAction = (action) => {
        return action.replace("ALLOCATE_", "").replace("_", " ");
    };

    const getRiskBadge = (risk) => {
        const colors = {
            'SAFE': 'bg-green-100 text-green-800',
            'MODERATE': 'bg-yellow-100 text-yellow-800',
            'CRITICAL': 'bg-red-100 text-red-800',
            'UNKNOWN': 'bg-gray-100 text-gray-800'
        };
        return colors[risk] || colors['UNKNOWN'];
    };

    return (
        <div className={`p-4 rounded shadow-sm bg-white mb-4 ${getPriorityColor(pScore)}`}>
            <div className="flex justify-between items-center">

                {/* LEFT: Case Info */}
                <div className="w-1/3">
                    <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-bold text-lg text-gray-800">{companyName}</h3>
                        {phone ? (
                            <button
                                onClick={() => {
                                    onCall(phone);
                                    setShowLogModal(true);
                                }}
                                className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-blue-100 text-blue-600 hover:bg-blue-200 transition-colors shadow-sm"
                                title={`Direct Browser Call to ${phone}`}
                            >
                                📞
                            </button>
                        ) : (
                            !editingPhone ? (
                                <button
                                    onClick={() => setEditingPhone(true)}
                                    className="text-xs bg-gray-100 text-gray-500 px-2 py-1 rounded hover:bg-gray-200"
                                    title="Add contact number"
                                >
                                    + Phone
                                </button>
                            ) : (
                                <div className="flex gap-1">
                                    <input
                                        type="tel"
                                        className="text-xs border rounded px-1 w-24"
                                        placeholder="Mobile No."
                                        value={newPhone}
                                        onChange={(e) => setNewPhone(e.target.value)}
                                    />
                                    <button onClick={handleUpdatePhone} className="text-xs text-green-600 font-bold">✓</button>
                                    <button onClick={() => setEditingPhone(false)} className="text-xs text-red-600 font-bold">×</button>
                                </div>
                            )
                        )}
                        <StatusBadge status={status} />
                    </div>
                    <p className="text-sm font-mono text-gray-600">Outstanding: <span className="font-semibold">₹{amount.toLocaleString()}</span></p>
                    <div className="flex items-center gap-2 mt-1">
                        {history.length > 0 && (
                            <button
                                onClick={() => setShowHistory(!showHistory)}
                                className="text-xs text-indigo-600 hover:text-indigo-800"
                            >
                                {showHistory ? '▼' : '▶'} {history.length} interaction{history.length !== 1 ? 's' : ''}
                            </button>
                        )}
                        {status !== 'CLOSED' && (
                            <button
                                onClick={() => setShowStatusModal(true)}
                                className="text-xs text-blue-600 hover:text-blue-800 font-medium"
                            >
                                📝 Update Status
                            </button>
                        )}
                    </div>
                </div>

                {/* CENTER: The Brain (RISKON Score) */}
                <div className="text-center w-1/3">
                    <div className="inline-block px-3 py-1 rounded bg-white border border-gray-100 shadow-sm">
                        <span className="block text-2xl font-bold text-gray-800">{(pScore * 100).toFixed(0)}%</span>
                        <span className="text-[10px] uppercase tracking-wide text-gray-500">Prob. to Pay</span>
                    </div>
                </div>

                {/* RIGHT: The Hands (Action Button) */}
                <div className="w-1/3 text-right">
                    <span className="inline-block px-3 py-1 text-xs font-semibold tracking-wide text-indigo-800 bg-indigo-100 rounded-full mb-2">
                        Recommended Strategy
                    </span>
                    <div className="font-bold text-indigo-600 mb-2">
                        {formatAction(suggestedAction)}
                    </div>

                    {/* ACTION BUTTONS */}
                    <div className="flex gap-2 justify-end">
                        <button
                            onClick={() => setShowLogModal(true)}
                            className="bg-purple-600 hover:bg-purple-700 text-white text-xs font-bold py-1 px-3 rounded shadow transition-colors"
                        >
                            📞 Log Call
                        </button>
                        <button
                            onClick={() => onPay(caseData)}
                            className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold py-1 px-3 rounded shadow transition-colors"
                        >
                            💳 Pay Now
                        </button>
                    </div>
                </div>
            </div>

            {/* INTERACTION HISTORY */}
            {showHistory && history.length > 0 && (
                <div className="mt-4 pt-3 border-t border-gray-200">
                    <h4 className="text-sm font-semibold text-gray-700 mb-2">Recent Interactions</h4>
                    <div className="space-y-2 max-h-60 overflow-y-auto">
                        {history.slice(0, 5).map((log) => (
                            <div key={log.id} className="bg-gray-50 p-2 rounded text-xs">
                                <div className="flex justify-between items-start mb-1">
                                    <span className="text-gray-500">
                                        {new Date(log.date).toLocaleDateString()} {new Date(log.date).toLocaleTimeString()}
                                    </span>
                                    <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${getRiskBadge(log.riskLevel)}`}>
                                        {log.riskLevel}
                                    </span>
                                </div>
                                <p className="text-gray-700">{log.text}</p>
                                {log.sentimentScore !== undefined && (
                                    <p className="text-gray-500 mt-1">Sentiment: {log.sentimentScore.toFixed(2)}</p>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* FOOTER: The Eyes (Sentinel Status) */}
            <div className="mt-4 pt-2 border-t border-gray-100 flex items-center justify-between text-xs">
                <div className="text-gray-400">AI Model: RISKON_ODE_v1.0</div>

                <div className="flex items-center">
                    <span className="font-semibold mr-2 text-gray-600">Sentinel Guard:</span>
                    {riskLevel === "LOW" || riskLevel === "SAFE" ? (
                        <span className="text-teal-600 flex items-center font-bold">
                            ✓ COMPLIANT
                        </span>
                    ) : (
                        <span className="text-red-600 flex items-center font-bold">
                            ⚠ RISK DETECTED
                        </span>
                    )}
                </div>
            </div>

            {/* LOG CALL MODAL */}
            {showLogModal && (
                <LogCallModal
                    caseId={case_id}
                    companyName={companyName}
                    onClose={() => setShowLogModal(false)}
                    onSuccess={() => {
                        setShowLogModal(false);
                        if (onLogCall) onLogCall();
                    }}
                />
            )}

            {/* UPDATE STATUS MODAL */}
            {showStatusModal && (
                <UpdateStatusModal
                    caseId={case_id}
                    currentStatus={status}
                    companyName={companyName}
                    onClose={() => setShowStatusModal(false)}
                    onSuccess={() => {
                        setShowStatusModal(false);
                        if (onLogCall) onLogCall(); // Refresh cases
                    }}
                />
            )}
        </div>
    );
};

export default CaseCard;
