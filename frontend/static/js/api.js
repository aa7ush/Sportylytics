/**
 * api.js - Centralized API calls for the Sportylytics frontend.
 * Points to the Render backend.
 */

const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://localhost:5000'
    : 'https://your-backend-on-render.com'; // REPLACE WITH YOUR RENDER URL

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
    siteConfig = await fetchData('/api/init');
    return siteConfig;
}
