const IS_DEVELOPMENT = import.meta.env.DEV;

// 1. Define Base URL
// - Development: Localhost (FastAPI defaults to 8000)
// - Production: Cloud Run URL (User Provided)
const BASE_URL = IS_DEVELOPMENT
    ? "http://127.0.0.1:8000"
    : "https://recoverai-backend-7k3o2t7hcq-uc.a.run.app";

// 2. Export API Endpoints
export const API = {
    LOGIN: `${BASE_URL}/token`,
    ANALYZE: `${BASE_URL}/api/v1/analyze`,
    INGEST: `${BASE_URL}/api/v1/ingest`,
    PAYMENT: `${BASE_URL}/api/v1/payment/create`,
    CASES: `${BASE_URL}/api/v1/cases`,
    LOG_INTERACTION: (caseId) => `${BASE_URL}/api/v1/cases/${caseId}/log_interaction`,
    UPDATE_STATUS: (caseId) => `${BASE_URL}/api/v1/cases/${caseId}/status`,
    CREATE_CASE: `${BASE_URL}/api/v1/cases/create`,
};

export default API;
