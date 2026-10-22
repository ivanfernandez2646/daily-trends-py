/** Where the end-to-end run puts the API, the app and their database. */
export const API_PORT = process.env.E2E_API_PORT ?? "5199";
export const WEB_PORT = process.env.E2E_WEB_PORT ?? "4173";
export const MONGO_URL = process.env.E2E_MONGO_URL ?? "mongodb://localhost:27017/daily-trends-e2e";

/** A second API whose tokens expire in seconds, and the app talking to it. */
export const EXPIRY_API_PORT = process.env.E2E_EXPIRY_API_PORT ?? "5198";
export const EXPIRY_WEB_PORT = process.env.E2E_EXPIRY_WEB_PORT ?? "4174";
export const EXPIRY_TOKEN_TTL_SECONDS = 10;

/** The administrator the global setup creates; test credentials, valid only in this database. */
export const ADMIN_EMAIL = "admin@example.com";
export const ADMIN_PASSWORD = "e2e-admin-password";
