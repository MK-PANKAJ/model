const IS_DEVELOPMENT = import.meta.env.DEV;

// 1. Define Base URL
// - Development: Localhost (FastAPI defaults to 8000)
// - Production: Cloud Run URL
const BASE_URL = IS_DEVELOPMENT
    ? "http://127.0.0.1:8000"
    : "https://recoverai-backend-1038460339762.us-central1.run.app";

// 2. Export API Endpoints
export const API = {
    LOGIN: `${BASE_URL}/token`,
    ANALYZE: `${BASE_URL}/api/v1/analyze`,
    INGEST: `${BASE_URL}/api/v1/ingest`,
    PAYMENT: `${BASE_URL}/api/v1/payment/create`,
};

export default API;
