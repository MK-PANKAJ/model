import React, { useState, useEffect } from 'react';
import CaseCard from './components/CaseCard';
import Login from './Login';
import API from './config';
import PaymentStatus from './components/PaymentStatus';
import AddCaseModal from './components/AddCaseModal';
import { Device } from '@twilio/voice-sdk';

const VirtualDialer = ({ phoneNumber, micState, onEnd }) => {
  const [connectStatus, setConnectStatus] = useState('Initiating VOIP...');

  useEffect(() => {
    if (phoneNumber) {
      setConnectStatus(micState === 'granted' ? 'Initiating VOIP...' : 'Awaiting Mic Access...');
      if (micState === 'granted') {
        setTimeout(() => setConnectStatus('Connecting Direct...'), 1000);
        setTimeout(() => setConnectStatus('LIVE: Secure AI Recording On'), 3000);
      }
    }
  }, [phoneNumber, micState]);

  if (!phoneNumber) return null;
  return (
    <div className="fixed bottom-6 right-6 w-80 bg-slate-900 text-white rounded-3xl shadow-[0_20px_50px_rgba(0,0,0,0.5)] p-6 border border-white/10 animate-slide-up z-50 backdrop-blur-md">
      <div className="flex justify-between items-center mb-6">
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${connectStatus.includes('LIVE') ? 'bg-red-500 animate-pulse' : 'bg-blue-400 animate-pulse'}`}></span>
          <span className="text-[10px] font-bold tracking-widest text-slate-400 uppercase">{connectStatus}</span>
        </div>
        <button onClick={onEnd} className="text-slate-500 hover:text-white transition-colors">✕</button>
      </div>

      <div className="text-center py-4">
        <div className="relative inline-block mb-4">
          <div className="absolute inset-0 bg-blue-500/20 rounded-full blur-xl animate-pulse"></div>
          <div className="relative w-20 h-20 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-full flex items-center justify-center shadow-lg">
            <span className="text-3xl">🎙️</span>
          </div>
        </div>
        <h4 className="text-xl font-bold text-white mb-1">+{phoneNumber}</h4>
        <p className="text-xs text-blue-400 font-semibold mb-6">Direct Browser Call (No SIM Required)</p>
      </div>

      <div className="grid grid-cols-2 gap-3 mb-6">
        <div className="bg-white/5 rounded-xl p-3 border border-white/5 text-center">
          <span className="block text-xl mb-1">{micState === 'granted' ? '✅' : '🚫'}</span>
          <span className="text-[10px] text-slate-500 uppercase">Microphone</span>
        </div>
        <div className="bg-white/5 rounded-xl p-3 border border-white/5 text-center">
          <span className="block text-xl mb-1">🎧</span>
          <span className="text-[10px] text-slate-500 uppercase">Headset</span>
        </div>
      </div>

      <button
        onClick={onEnd}
        className="w-full bg-red-500 hover:bg-red-600 text-white py-3 rounded-2xl font-bold shadow-lg shadow-red-500/20 transition-all transform active:scale-95"
      >
        End Direct Call
      </button>

      <p className="text-[9px] text-slate-500 text-center mt-4">Powered by RecoverAI WebRTC Gateway</p>
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
  const [micPermission, setMicPermission] = useState('prompt'); // 'prompt', 'granted', 'denied'
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
    // Find the case ID for this phone number to track it
    const relatedCase = analyzedCases.find(c => c.phone === debtorPhone);
    const caseId = relatedCase ? relatedCase.case_id : "UNKNOWN";

    setActiveCall(debtorPhone);

    try {
      // 1. Get Token from Backend
      const tokenResp = await fetch(API.TELEPHONY_TOKEN, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (!tokenResp.ok) throw new Error("Could not fetch VOIP token");
      const { token: voiceToken } = await tokenResp.json();

      // 2. Setup Twilio Device
      const device = new Device(voiceToken, {
        codecPreferences: ['opus', 'pcmu'],
        logLevel: 0
      });

      // Request Microphone Permission explicitly
      try {
        await navigator.mediaDevices.getUserMedia({ audio: true });
        setMicPermission('granted');
      } catch (err) {
        setMicPermission('denied');
        alert("Microphone access is required for Browser Dialing.");
        setActiveCall(null);
        return;
      }

      await device.register();

      // 3. Connect Call with metadata
      const call = await device.connect({
        params: {
          To: debtorPhone,
          case_id: caseId
        }
      });

      // 4. Handle Disconnect
      call.on('disconnect', () => {
        console.log("Call disconnected");
        setActiveCall(null);
        // Wait 5s for backend AI analysis loop to complete, then refresh UI
        setTimeout(() => fetchCases(token), 5000);
        alert("Call Ended. AI Analysis in progress...");
      });

      call.on('error', (error) => {
        console.error("Twilio Call Error:", error);
        setActiveCall(null);
        alert("Call failed: " + error.message);
      });

    } catch (err) {
      console.error("Twilio Device/Call Error:", err);
      alert("Failed to connect call. Ensure backend is running and Twilio credentials are valid.");
      setActiveCall(null);
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
              <label className="block text-sm font-medium text-gray-700 mb-1">Agent Identity (Internal)</label>
              <input
                type="text"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 outline-none focus:ring-2 focus:ring-indigo-500"
                placeholder="Agent Name or ID"
                value={agentSettings.callerId}
                onChange={(e) => {
                  const val = e.target.value;
                  setAgentSettings({ ...agentSettings, callerId: val });
                  localStorage.setItem('agentCallerId', val);
                }}
              />
              <p className="text-[10px] text-gray-400 mt-2">This is your internal identifier. Outgoing calls use the company's Twilio Number.</p>
            </div>
            Barb            <div className="flex justify-end">
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
        micState={micPermission}
        onEnd={() => setActiveCall(null)}
      />
    </div>
  );
}

export default App;
