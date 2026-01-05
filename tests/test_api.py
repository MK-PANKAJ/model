import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_check():
    """Verify API is online"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "active", "system": "RecoverAI Agentic Core"}

def test_riskon_logic():
    """Verify High Risk Logic (Old Debt = Low Score)"""
    payload = {
        "case_id": "TEST_001",
        "company_name": "Test Corp",
        "amount": 5000.0,
        "initial_score": 0.8,
        "age_days": 180, # Very old debt
        "history_logs": []
    }
    response = client.post("/api/v1/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    # Expectation: 180 days old should have low score
    assert data["riskon_score"] < 0.20 
    assert data["allocation_decision"]["action"] == "ALLOCATE_LEGAL"

def test_sentinel_guard_violation():
    """Verify Sentinel catches bad words"""
    payload = {"text": "I will send the police to arrest you"}
    response = client.post("/api/v1/sentinel/audit", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert data["risk_level"] == "CRITICAL"
    assert "VIOLATION_KEYWORD" in data["violation_flags"][0]
