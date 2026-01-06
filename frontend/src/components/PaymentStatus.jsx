import React, { useEffect, useState } from 'react';

export default function PaymentStatus({ onClose }) {
    const [status, setStatus] = useState(null); // 'success' | 'cancelled' | null
    const [caseId, setCaseId] = useState(null);

    useEffect(() => {
        const params = new URLSearchParams(window.location.search);
        const paymentParam = params.get('payment');

        if (paymentParam === 'success') {
            setStatus('success');
            setCaseId(params.get('case_id'));
        } else if (paymentParam === 'cancelled') {
            setStatus('cancelled');
        }
    }, []);

    if (!status) return null;

    const handleClear = () => {
        // Clear URL params without reload
        window.history.pushState({}, document.title, window.location.pathname);
        setStatus(null);
        if (onClose) onClose();
    };

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 animate-fade-in">
            <div className="bg-white p-8 rounded-2xl shadow-2xl max-w-md w-full text-center border border-gray-100">

                {status === 'success' && (
                    <>
                        <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
                            <span className="text-4xl">🎉</span>
                        </div>
                        <h2 className="text-3xl font-bold text-gray-800 mb-2">Payment Successful!</h2>
                        <p className="text-gray-500 mb-6">
                            Thank you for settling case <span className="font-mono font-bold text-gray-800">{caseId || 'Unknown'}</span>.
                            The debt has been cleared from our records.
                        </p>
                        <button
                            onClick={handleClear}
                            className="w-full bg-green-600 text-white font-bold py-3 px-6 rounded-xl hover:bg-green-700 transition transform hover:scale-[1.02]"
                        >
                            Return to Dashboard
                        </button>
                    </>
                )}

                {status === 'cancelled' && (
                    <>
                        <div className="w-20 h-20 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-6">
                            <span className="text-4xl">⚠️</span>
                        </div>
                        <h2 className="text-2xl font-bold text-gray-800 mb-2">Payment Cancelled</h2>
                        <p className="text-gray-500 mb-6">
                            The transaction was not completed. No charges were made to your card.
                        </p>
                        <button
                            onClick={handleClear}
                            className="w-full bg-gray-800 text-white font-bold py-3 px-6 rounded-xl hover:bg-gray-700 transition transform hover:scale-[1.02]"
                        >
                            Try Again
                        </button>
                    </>
                )}

            </div>
        </div>
    );
}
