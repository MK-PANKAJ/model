import React, { useState, useEffect } from 'react';
import CaseCard from './components/CaseCard';

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

  // SIMULATE API CALL (To Python Backend)
  // In real life, this fetches from http://localhost:8000/api/v1/analyze
  const runAnalysis = async () => {
    setLoading(true);
    const results = [];
    
    // We simulate the API call latency and logic here for the demo
    // since we might not have the Python server running strictly on port 8000 in this view
    for (let c of MOCK_CASES) {
       // Mocking the Backend Response based on our known logic
       // High interaction + Low Age = High Score
       let score = c.age_days > 30 ? 0.45 : 0.88; 
       if(c.companyName === "Global Trade Ltd") score = 0.42;
       
       let action = score > 0.7 ? "ALLOCATE_DIGITAL" : "ALLOCATE_AGENCY";
       
       results.push({
         ...c,
         pScore: score,
         suggestedAction: action,
         riskLevel: "LOW", // Default
         violationTag: ""
       });
    }
    
    setTimeout(() => {
      setAnalyzedCases(results.sort((a,b) => b.pScore - a.pScore)); // Sort by Priority
      setLoading(false);
    }, 800);
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-gray-800">RecoverAI <span className="text-blue-600">SuRaksha Portal</span></h1>
        <p className="text-gray-500">Agentic Debt Recovery System</p>
      </header>

      <div className="mb-6">
        <button 
          onClick={runAnalysis}
          disabled={loading}
          className="bg-indigo-600 text-white px-6 py-2 rounded-lg shadow hover:bg-indigo-700 transition"
        >
          {loading ? "Processing ODE Models..." : "Run Daily Allocation Batch"}
        </button>
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
