import React, { useState, useEffect } from 'react';
import CaseCard from './components/CaseCard';
import Login from './Login';
import API from './config';
import PaymentStatus from './components/PaymentStatus';
import AddCaseModal from './components/AddCaseModal';

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
  const [loading, setLoading] = useState(false);
  const [token, setToken] = useState(null);
  const [showAddModal, setShowAddModal] = useState(false);

  // Check for existing session
  useEffect(() => {
    const savedToken = localStorage.getItem('token');
    if (savedToken) {
      setToken(savedToken);
      fetchCases(savedToken); // Load data immediately
    }
  }, []);

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

      // We iterate over the REAL cases now
      for (let c of analyzedCases) {
        if (c.pScore) continue; // Skip already analyzed

        const payload = {
          case_id: c.case_id.replace("C-", ""), // Send ID only
          company_name: c.companyName,
          amount: c.amount,
          initial_score: c.initial_score,
          age_days: c.age_days,
          history_logs: c.history
        };

        const response = await fetch(API_URL, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          },
          body: JSON.stringify(payload)
        });
      }
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
        window.location.href = data.payment_url;
      } else {
        alert("Error: " + JSON.stringify(data));
      }
    } catch (err) {
      console.error(err);
      alert("Payment Error: " + err.message);
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
        <button
          onClick={handleLogout}
          className="text-sm text-red-500 hover:text-red-700 border border-red-200 px-3 py-1 rounded"
        >
          Logout
        </button>
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
          <CaseCard key={c.case_id} caseData={c} onPay={handlePayment} />
        ))}
      </div>
    </div>
  );
}

export default App;
