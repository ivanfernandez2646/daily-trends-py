/** Where the end-to-end run puts the API, the app and their database. */
export const API_PORT = process.env.E2E_API_PORT ?? "5199";
export const WEB_PORT = process.env.E2E_WEB_PORT ?? "4173";
export const MONGO_URL = process.env.E2E_MONGO_URL ?? "mongodb://localhost:27017/daily-trends-e2e";
