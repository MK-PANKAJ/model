import React, { useState, useEffect } from 'react';
import CaseCard from './components/CaseCard';
import Login from './Login';
import API from './config';
import PaymentStatus from './components/PaymentStatus';
import AddCaseModal from './components/AddCaseModal';

const VirtualDialer = ({ phoneNumber, callerId, onEnd }) => {
  const [connectStatus, setConnectStatus] = useState('Requesting Bridge...');

  useEffect(() => {
    if (phoneNumber) {
      setConnectStatus('Requesting Bridge...');
      setTimeout(() => setConnectStatus('Ringing Agent...'), 1500);
      setTimeout(() => setConnectStatus('Connecting Debtor...'), 3500);
      setTimeout(() => setConnectStatus('LIVE: Secure Recording On'), 6000);
    }
  }, [phoneNumber]);

  if (!phoneNumber) return null;
  return (
    <div className="fixed bottom-6 right-6 w-80 bg-gray-900 text-white rounded-2xl shadow-2xl p-5 border border-gray-700 animate-slide-up z-50">
      <div className="flex justify-between items-center mb-4">
        <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${connectStatus.includes('LIVE') ? 'bg-red-600 animate-pulse' : 'bg-indigo-600'}`}>
          {connectStatus}
        </span>
        <button onClick={onEnd} className="text-gray-400 hover:text-white">✕</button>
      </div>
      <div className="text-center py-4">
        <div className="w-16 h-16 bg-indigo-500 rounded-full mx-auto flex items-center justify-center mb-3 shadow-lg shadow-indigo-500/20">
          <span className="text-2xl">⚡</span>
        </div>
        <h4 className="font-bold text-lg">{phoneNumber}</h4>
        <div className="mt-3 space-y-1">
          <p className="text-[10px] text-gray-500">VOIP PATH: CLOUD BRIDGE</p>
          <p className="text-[10px] text-gray-400 font-mono">ID: {callerId || 'DUMMY-AGENT'}</p>
        </div>
      </div>
      <div className="bg-black/30 rounded-lg p-3 mt-4 border border-white/5">
        <div className="flex items-center gap-3">
          <div className="text-xl">📞</div>
          <div className="flex-1">
            <p className="text-[10px] text-gray-500 uppercase tracking-widest">Bridging To</p>
            <p className="text-xs font-semibold text-indigo-300">Your Real Settings Number</p>
          </div>
        </div>
      </div>
      <button
        onClick={onEnd}
        className="w-full bg-red-600/20 text-red-500 border border-red-600/50 hover:bg-red-600 hover:text-white py-2 rounded-lg text-sm font-bold mt-4 transition-all"
      >
        Discard Call
      </button>
    </div>
  );
};

// MOCK DATA SIMULATING THE ERP
const MOCK_CASES = [
  {
    case_id: "C-101",
    companyName: "Acme Logistics",
    amount: 15400,
    initial_score: 0.85,
    age_days: 12,
    history: [2, 5]
  },
  {
    case_id: "C-102",
    companyName: "Global Trade Ltd",
    amount: 42000,
    initial_score: 0.60,
    age_days: 45,
    history: []
  },
  {
    case_id: "C-103",
    companyName: "StartUp Inc",
    amount: 2100,
    initial_score: 0.90,
    age_days: 5,
    history: []
  }
];

function App() {
  const [analyzedCases, setAnalyzedCases] = useState([]);
  const [activeCall, setActiveCall] = useState(null);
  const [loading, setLoading] = useState(false);
  const [token, setToken] = useState(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [agentSettings, setAgentSettings] = useState({
    callerId: localStorage.getItem('agentCallerId') || ''
  });
  const [paymentModal, setPaymentModal] = useState({ show: false, link: '', caseId: '', company: '' });

  // Check for existing session
  useEffect(() => {
    const savedToken = localStorage.getItem('token');
    if (savedToken) {
      setToken(savedToken);
      fetchCases(savedToken); // Load data immediately
    }
  }, []);

  // 2. AUTO-REFRESH (POLLING) TO UPDATE STATUS
  // This ensures the Agent sees "PAID" automatically when the Debtor pays remotely
  useEffect(() => {
    if (!token) return;

    // Poll the database every 10 seconds to check for status updates
    const interval = setInterval(() => {
      fetchCases(token);
    }, 10000); // 10 seconds

    return () => clearInterval(interval);
  }, [token]);

  const fetchCases = async (authToken) => {
    try {
      setLoading(true);
      const response = await fetch(API.CASES, {
        headers: { "Authorization": `Bearer ${authToken}` }
      });
      if (response.status === 401) {
        handleLogout();
        return;
      }
      const data = await response.json();
      setAnalyzedCases(data);
    } catch (err) {
      console.error("Failed to load cases:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setToken(null);
  };

  // LIVE API CALL (To Google Cloud Run)
  // LIVE API CALL (To Google Cloud Run)
  const runAnalysis = async () => {
    setLoading(true);
    const API_URL = API.ANALYZE;

    try {
      // Fetch fresh list from DB first (Self-Healing)
      await fetchCases(token);

      // Map valid cases to fetch promises
      const analysisPromises = analyzedCases
        .filter(c => !c.pScore) // Skip already analyzed
        .map(c => {
          const payload = {
            case_id: c.case_id.replace("C-", ""), // Send ID only
            company_name: c.companyName,
            amount: c.amount,
            initial_score: c.initial_score,
            age_days: c.age_days,
            history_logs: (c.history || []).map(h => h.id || h) // Handle both objects and raw day IDs
          };

          return fetch(API_URL, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify(payload)
          });
        });

      // Execute all in parallel
      await Promise.all(analysisPromises);

      // Reload to see results
      await fetchCases(token);

    } catch (err) {
      console.error("Batch Analysis Error:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setLoading(true);
    const formData = new FormData();
    formData.append("file", file);

    const UPLOAD_URL = API.INGEST;

    try {
      const response = await fetch(UPLOAD_URL, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`
        },
        body: formData
      });

      if (!response.ok) throw new Error("Upload Failed");
      const result = await response.json();
      alert(`Ingestion Complete! Inserted: ${result.inserted}, Errors: ${result.errors.length}`);
    } catch (err) {
      console.error(err);
      alert("Upload failed: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handlePayment = async (caseData) => {
    const PAYMENT_URL = API.PAYMENT;

    try {
      const response = await fetch(PAYMENT_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          case_id: caseData.case_id,
          amount: caseData.amount
        })
      });

      if (!response.ok) throw new Error("Payment Link Creation Failed");

      const data = await response.json();
      if (data.payment_url) {
        // Show the link to the Agent instead of redirecting
        setPaymentModal({
          show: true,
          link: data.payment_url,
          caseId: caseData.case_id,
          company: caseData.companyName
        });
      } else {
        alert("Error: " + JSON.stringify(data));
      }
    } catch (err) {
      console.error(err);
      alert("Payment Error: " + err.message);
    }
  };

  const handleDirectCall = async (debtorPhone) => {
    setActiveCall(debtorPhone);
    // Log the Direct Dial event to the backend
    try {
      await fetch(API.INITIATE_BRIDGE, {
        method: 'POST',
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          agent_phone: "BROWSER_AGENT", // Signifies direct browser dial
          debtor_phone: debtorPhone
        })
      });
    } catch (err) {
      console.error("Direct Dial Tracking Failed:", err);
    }
  };

  if (!token) {
    return <Login onLogin={(t) => {
      localStorage.setItem('token', t);
      setToken(t);
      fetchCases(t);
    }} />;
  }

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <PaymentStatus />
      <header className="mb-8 flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-800">RecoverAI <span className="text-blue-600">SuRaksha Portal</span></h1>
          <p className="text-gray-500">Agentic Debt Recovery System</p>
        </div>
        <div className="flex items-center gap-4">
          <button
            onClick={() => setShowSettings(true)}
            className="p-2 text-gray-500 hover:bg-gray-100 rounded-full transition-colors"
            title="Agent Settings"
          >
            ⚙️
          </button>
          <button
            onClick={handleLogout}
            className="text-sm text-red-500 hover:text-red-700 border border-red-200 px-3 py-1 rounded"
          >
            Logout
          </button>
        </div>
      </header>

      <div className="mb-6 flex gap-4">
        <button
          onClick={runAnalysis}
          disabled={loading}
          className="bg-indigo-600 text-white px-6 py-2 rounded-lg shadow hover:bg-indigo-700 transition"
        >
          {loading ? "Processing ODE Models..." : "Run Daily Allocation Batch"}
        </button>

        <label className="bg-emerald-600 text-white px-6 py-2 rounded-lg shadow hover:bg-emerald-700 transition cursor-pointer">
          {loading ? "Uploading..." : "Upload FedEx CSV"}
          <input type="file" onChange={handleFileUpload} accept=".csv" className="hidden" disabled={loading} />
        </label>

        <button
          onClick={() => setShowAddModal(true)}
          className="bg-purple-600 text-white px-6 py-2 rounded-lg shadow hover:bg-purple-700 transition"
        >
          + Add Case Manually
        </button>
      </div>

      {showAddModal && (
        <AddCaseModal
          onClose={() => setShowAddModal(false)}
          onSuccess={() => {
            fetchCases(token);
            alert('Case added successfully!');
          }}
        />
      )}

      <div className="grid gap-6">
        {analyzedCases.length === 0 && !loading && (
          <div className="text-center py-20 bg-white rounded border border-dashed border-gray-300">
            <p className="text-gray-400">No cases allocated. Click "Run Batch" to ingest from ERP.</p>
          </div>
        )}

        {analyzedCases.map((c) => (
          <CaseCard
            key={c.case_id}
            caseData={c}
            onPay={handlePayment}
            onLogCall={() => fetchCases(token)}
            onCall={handleDirectCall}
          />
        ))}
      </div>

      {paymentModal && paymentModal.show && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 backdrop-blur-sm">
          <div className="bg-white p-6 rounded-xl shadow-2xl w-[32rem] border border-gray-100">
            <h3 className="text-xl font-bold text-gray-800 mb-2">Payment Link Generated</h3>
            <p className="text-sm text-gray-500 mb-4">
              Share this secure link with <span className="font-semibold text-gray-700">{paymentModal.company}</span>.
              When they pay, this case will automatically mark as PAID.
            </p>

            <div className="flex gap-2 mb-6">
              <input
                type="text"
                readOnly
                value={paymentModal.link}
                className="w-full bg-gray-50 border border-gray-200 text-gray-600 text-sm rounded px-3 py-2 focus:ring-2 focus:ring-indigo-500 outline-none"
              />
              <button
                onClick={() => {
                  navigator.clipboard.writeText(paymentModal.link);
                  alert("Link copied to clipboard!");
                }}
                className="bg-gray-200 hover:bg-gray-300 text-gray-700 px-4 py-2 rounded font-medium text-sm transition"
              >
                Copy
              </button>
            </div>

            <div className="flex justify-end">
              <button
                onClick={() => setPaymentModal({ ...paymentModal, show: false })}
                className="text-gray-500 hover:text-gray-700 text-sm font-medium px-4 py-2"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* SETTINGS MODAL */}
      {showSettings && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 backdrop-blur-sm">
          <div className="bg-white p-6 rounded-xl shadow-2xl w-96 border border-gray-100">
            <h3 className="text-xl font-bold text-gray-800 mb-4">Agent Settings</h3>
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-1">Your Real Number (Caller ID)</label>
              <input
                type="tel"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 outline-none focus:ring-2 focus:ring-indigo-500"
                placeholder="+91 98765 43210"
                value={agentSettings.callerId}
                onChange={(e) => {
                  const val = e.target.value;
                  setAgentSettings({ ...agentSettings, callerId: val });
                  localStorage.setItem('agentCallerId', val);
                }}
              />
              <p className="text-[10px] text-gray-400 mt-2">This number will be displayed to debtors when you use the Recovery Bridge.</p>
            </div>
            <div className="flex justify-end">
              <button
                onClick={() => setShowSettings(false)}
                className="bg-indigo-600 text-white px-6 py-2 rounded-lg font-bold hover:bg-indigo-700 transition"
              >
                Save & Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* GLOBAL VIRTUAL DIALER */}
      <VirtualDialer
        phoneNumber={activeCall}
        onEnd={() => setActiveCall(null)}
      />
    </div>
  );
}

export default App;
