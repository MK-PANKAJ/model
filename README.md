# PROJECT CHARTER: RecoverAI

**Project Name:** RecoverAI (External Debt Recovery Optimization)
**Sponsor:** FedEx Finance / Digital Transformation Office
**Date:** January 06, 2026
**Version:** 1.0 (MVP)

---

## 1. Executive Summary
FedEx’s current external debt recovery process operates as a manual "black box," relying on static spreadsheets. **RecoverAI** is a digital ecosystem that transforms this process by introducing **Agentic AI Allocation**, **Probabilistic Scoring (RISKON)**, and **Real-Time Governance**. This moves FedEx from manual administration to intelligent automation.

---

## 2. Problem Statement (The 4 Fractures)
1.  **Operational Fracture:** Manual "Spreadsheet Shuffle" causes delays.
2.  **Intelligence Gap:** "Spray and Pray" prioritization wastes effort.
3.  **Governance Blind Spot:** Lack of real-time visibility into DCA behavior.
4.  **Security Vulnerability:** Sensitive PII on insecure laptops.

---

## 3. Capabilities & Scope (Phase 1 MVP)

### Module 1: Agentic Allocation Core ("The Hands")
*   **Function:** Automated ingestion and routing.
*   **Code:** `modules/allocation_core/`

### Module 2: RISK-ON Probability Engine ("The Brain")
*   **Function:** ODE-based Probability Scoring.
*   **Code:** `modules/riskon_engine/`

### Module 3: Sentinel Compliance Guardrail ("The Eyes")
*   **Function:** Real-time NLP analysis for compliance.
*   **Code:** `modules/sentinel_guard/`

### Module 4: SuRaksha Portal ("The Face")
*   **Function:** Unified Web Dashboard for Agents.
*   **Code:** `frontend/`

---

## 4. Quick Start

### Docker (Recommended)
```bash
docker-compose up --build
```

### Manual
1.  **Backend:** `uvicorn main:app --reload`
2.  **Frontend:** `cd frontend && npm install && npm run dev`

---

