// API configuration
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// API functions
async function fetchAPI(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;

    const defaultHeaders = {
        'Content-Type': 'application/json',
    };

    const fetchOptions = {
        method: 'GET',
        headers: defaultHeaders,
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

export async function getProgress() {
    return fetchAPI('/stats/progress');
}

export async function getFunctions(limit = 50) {
    return fetchAPI(`/functions?limit=${limit}&include_stats=true`);
}

export async function searchCode(query, fuzzy = false) {
    if (!query.trim()) return [];
    return fetchAPI(`/search?q=${encodeURIComponent(query)}&limit=20&fuzzy=${fuzzy}`);
}

export async function analyzeStacktrace(rawStacktrace) {
    return fetchAPI('/analyze', {
        method: 'POST',
        body: JSON.stringify({ stacktrace: rawStacktrace }),
    });
}

export async function getFunctionCode(functionId) {
    return fetchAPI(`/code/${functionId}`);
} 