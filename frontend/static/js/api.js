/**
 * api.js - Centralized API calls for the Sportylytics frontend.
 * Points to the Render backend.
 */

const API_BASE = 'https://sportylytics-api.onrender.com'; // TODO: Update this with your actual Render URL if different

async function fetchData(endpoint) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        return await response.json();
    } catch (e) {
        console.error("Fetch error:", e);
        return null;
    }
}

// Global config singleton
let siteConfig = null;

async function getSiteConfig() {
    if (siteConfig) return siteConfig;
    siteConfig = await fetchData('/init');
    return siteConfig;
}
