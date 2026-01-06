import React from 'react';

// The "Smart Card" that displays the ODE Score and Suggested Action
const CaseCard = ({ caseData, onPay }) => {
    // Destructure data from the RISKON Engine
    const { companyName, amount, pScore, suggestedAction, riskLevel, violationTag } = caseData;

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

    return (
        <div className={`p-4 rounded shadow-sm bg-white mb-4 ${getPriorityColor(pScore)}`}>
            <div className="flex justify-between items-center">

                {/* LEFT: Case Info */}
                <div className="w-1/3">
                    <h3 className="font-bold text-lg text-gray-800">{companyName}</h3>
                    <p className="text-sm font-mono text-gray-600">Outstanding: <span className="font-semibold">₹{amount.toLocaleString()}</span></p>
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

                    {/* PAY NOW BUTTON (Stripe) */}
                    <button
                        onClick={() => onPay(caseData)}
                        className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold py-1 px-3 rounded shadow transition-colors"
                    >
                        Pay Now 💳
                    </button>
                </div>
            </div>

            {/* FOOTER: The Eyes (Sentinel Status) */}
            <div className="mt-4 pt-2 border-t border-gray-100 flex items-center justify-between text-xs">
                <div className="text-gray-400">AI Model: RISKON_ODE_v1.0</div>

                <div className="flex items-center">
                    <span className="font-semibold mr-2 text-gray-600">Sentinel Guard:</span>
                    {riskLevel === "LOW" ? (
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
        </div>
    );
};

export default CaseCard;
