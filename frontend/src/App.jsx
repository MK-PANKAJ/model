import React, { useState, useEffect } from 'react';
import CaseCard from './components/CaseCard';
import Login from './Login';

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

  // Check for existing session
  useEffect(() => {
    const savedToken = localStorage.getItem('token');
    if (savedToken) setToken(savedToken);
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('token');
    setToken(null);
  };

  // LIVE API CALL (To Google Cloud Run)
  const runAnalysis = async () => {
    setLoading(true);
    const results = [];
    const API_URL = "https://recoverai-backend-1038460339762.us-central1.run.app/api/v1/analyze";

    try {
      for (let c of MOCK_CASES) {
        // We send the mock case structure to the REAL brain
        const response = await fetch(API_URL, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}` // AUTH HEADER ADDED
          },
          body: JSON.stringify(c)
        });

        if (response.status === 401) {
          handleLogout();
          throw new Error("Session Expired");
        }

        if (!response.ok) throw new Error("API Connection Failed");

        const data = await response.json();

        // Merge the AI Brain result with our Case Data
        results.push({
          ...c,
          pScore: data.riskon_score,
          suggestedAction: data.allocation_decision.action,
          riskLevel: "LOW", // Sentinel default
          violationTag: ""
        });
      }
    } catch (err) {
      console.error("Cloud Connection Error:", err);
      if (err.message !== "Session Expired") {
        alert("Failed to connect to Cloud Backend. Is it running?");
      }
    }

    setAnalyzedCases(results.sort((a, b) => b.pScore - a.pScore));
    setLoading(false);
    setAnalyzedCases(results.sort((a, b) => b.pScore - a.pScore));
    setLoading(false);
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setLoading(true);
    const formData = new FormData();
    formData.append("file", file);

    const UPLOAD_URL = "https://recoverai-backend-1038460339762.us-central1.run.app/api/v1/ingest";

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

  if (!token) {
    return <Login onLogin={(t) => {
      localStorage.setItem('token', t);
      setToken(t);
    }} />;
  }

  return (
    <div className="min-h-screen bg-gray-50 p-8">
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
      </div>

      <div className="grid gap-6">
        {analyzedCases.length === 0 && !loading && (
          <div className="text-center py-20 bg-white rounded border border-dashed border-gray-300">
            <p className="text-gray-400">No cases allocated. Click "Run Batch" to ingest from ERP.</p>
          </div>
        )}

        {analyzedCases.map((c) => (
          <CaseCard key={c.case_id} caseData={c} />
        ))}
      </div>
    </div>
  );
}

export default App;
