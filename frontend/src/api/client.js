// API Client Module
import { CONFIG } from '../config/constants.js';

class APIClient {
    constructor(baseURL = CONFIG.API_BASE_URL) {
        this.baseURL = baseURL;
        this.defaultHeaders = {
            'Content-Type': 'application/json',
        };
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        
        const fetchOptions = {
            method: 'GET',
            headers: this.defaultHeaders,
            ...options,
        };

        try {
            const response = await fetch(url, fetchOptions);
            if (!response.ok) {
                throw new Error(`API Error: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('API fetch failed:', error);
            throw error;
        }
    }

    // Progress endpoints
    async getProgress() {
        return this.request('/stats/progress');
    }

    // Function endpoints
    async getFunctions(limit = CONFIG.FUNCTIONS_LIMIT) {
        return this.request(`/functions?limit=${limit}&include_stats=true`);
    }

    async getFunctionCode(functionId) {
        return this.request(`/code/${functionId}`);
    }

    // Search endpoints
    async searchCode(query, fuzzy = false) {
        if (!query.trim()) return [];
        return this.request(`/search?q=${encodeURIComponent(query)}&limit=${CONFIG.SEARCH_LIMIT}&fuzzy=${fuzzy}`);
    }

    // Analysis endpoints
    async analyzeStacktrace(stacktrace) {
        return this.request('/analyze', {
            method: 'POST',
            body: JSON.stringify({ stacktrace }),
        });
    }
}

export default new APIClient(); 