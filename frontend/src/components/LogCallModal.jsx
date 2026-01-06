import { useState } from 'react';
import API from '../config';

export default function LogCallModal({ caseId, companyName, onClose, onSuccess }) {
    const [interactionText, setInteractionText] = useState('');
    const [complianceResult, setComplianceResult] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const checkCompliance = async () => {
        if (!interactionText.trim()) {
            setError('Please enter interaction text');
            return;
        }

        setLoading(true);
        setError('');

        try {
            const token = localStorage.getItem('token');
            const response = await fetch(API.LOG_INTERACTION(caseId), {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ text: interactionText })
            });

            if (!response.ok) throw new Error('Failed to log interaction');

            const data = await response.json();
            setComplianceResult(data.compliance);

            // Auto-close and refresh after successful log
            setTimeout(() => {
                onSuccess();
                onClose();
            }, 2000);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const getRiskColor = (riskLevel) => {
        switch (riskLevel) {
            case 'SAFE': return 'bg-green-100 text-green-800 border-green-300';
            case 'MODERATE': return 'bg-yellow-100 text-yellow-800 border-yellow-300';
            case 'CRITICAL': return 'bg-red-100 text-red-800 border-red-300';
            default: return 'bg-gray-100 text-gray-800 border-gray-300';
        }
    };

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-white rounded-xl shadow-2xl p-6 w-full max-w-2xl">
                <div className="flex justify-between items-center mb-4">
                    <div>
                        <h2 className="text-2xl font-bold text-gray-800">Log Call</h2>
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
                            What did you say to the debtor?
                        </label>
                        <textarea
                            className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none"
                            rows="6"
                            value={interactionText}
                            onChange={(e) => setInteractionText(e.target.value)}
                            placeholder='Example: "Called customer about invoice #1234. They agreed to pay by Friday."'
                            disabled={loading || complianceResult}
                        />
                        <div className="flex justify-between mt-1">
                            <span className="text-xs text-gray-500">
                                {interactionText.length} characters
                            </span>
                            {complianceResult && (
                                <span className="text-xs text-green-600 font-medium">
                                    ✓ Logged successfully
                                </span>
                            )}
                        </div>
                    </div>

                    {/* Compliance Result Display */}
                    {complianceResult && (
                        <div className={`border-2 rounded-lg p-4 ${getRiskColor(complianceResult.risk_level)}`}>
                            <div className="flex items-center gap-2 mb-2">
                                <span className="text-lg font-bold">
                                    {complianceResult.risk_level === 'SAFE' && '✓'}
                                    {complianceResult.risk_level === 'MODERATE' && '⚠'}
                                    {complianceResult.risk_level === 'CRITICAL' && '⛔'}
                                </span>
                                <span className="font-semibold">
                                    {complianceResult.risk_level} Risk Level
                                </span>
                            </div>

                            {complianceResult.violation_flags && complianceResult.violation_flags.length > 0 && (
                                <div className="mt-2">
                                    <p className="text-sm font-medium mb-1">Violations Detected:</p>
                                    <ul className="text-sm list-disc list-inside">
                                        {complianceResult.violation_flags.map((flag, idx) => (
                                            <li key={idx}>{flag}</li>
                                        ))}
                                    </ul>
                                </div>
                            )}

                            <div className="mt-2 text-sm">
                                <strong>Sentiment Score:</strong> {complianceResult.sentiment_score?.toFixed(2) || 'N/A'}
                            </div>
                        </div>
                    )}

                    <div className="flex gap-3 pt-2">
                        <button
                            type="button"
                            onClick={onClose}
                            className="flex-1 bg-gray-100 text-gray-700 py-2 px-4 rounded-lg hover:bg-gray-200 transition"
                        >
                            {complianceResult ? 'Close' : 'Cancel'}
                        </button>
                        {!complianceResult && (
                            <button
                                onClick={checkCompliance}
                                disabled={loading || !interactionText.trim()}
                                className="flex-1 bg-indigo-600 text-white py-2 px-4 rounded-lg hover:bg-indigo-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                {loading ? 'Checking Compliance...' : 'Log & Check Compliance'}
                            </button>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
