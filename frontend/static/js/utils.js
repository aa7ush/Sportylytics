/**
 * utils.js - Formatting and status helpers.
 */

const exchangeRates = {
    'EUR': 1.0, 'USD': 1.08, 'GBP': 0.84, 'INR': 91.2, 
    'SAR': 4.05, 'JPY': 163.5, 'CNY': 7.82, 'AED': 3.97
};

const currencySymbols = {
    'EUR': '€', 'USD': '$', 'GBP': '£', 'INR': '₹', 
    'SAR': 'ر.س', 'JPY': '¥', 'CNY': '¥', 'AED': 'د.إ'
};

function formatCurrency(value, currency) {
    if (!value || value <= 0) return '-';
    const rate = exchangeRates[currency] || 1.0;
    const converted = value * rate;
    const symbol = currencySymbols[currency] || '';
    
    if (converted >= 1000000) return `${symbol}${(converted / 1000000).toFixed(1)}M`;
    if (converted >= 1000) return `${symbol}${(converted / 1000).toFixed(0)}K`;
    return symbol + Math.round(converted).toLocaleString();
}

function getRatingColor(rating) {
    const r = parseFloat(rating);
    if (!r || r === 0) return "transparent";
    if (r >= 7.5) return "#07812f"; // Excellence - Green
    if (r >= 6.8) return "#e6b014"; // Average - Yellow/Orange
    return "#ce1a1a"; // Poor - Red
}

function formatDate(ts) {
    if (!ts) return "N/A";
    return new Date(ts * 1000).toLocaleDateString([], { day: '2-digit', month: 'short', year: 'numeric' });
}
