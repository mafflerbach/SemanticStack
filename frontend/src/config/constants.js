// Application Constants and Configuration

export const CONFIG = {
    // API Configuration
    API_BASE_URL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
    
    // Refresh Settings
    AUTO_REFRESH_INTERVAL: 30000, // 30 seconds
    
    // Search Settings
    SEARCH_LIMIT: 20,
    FUNCTIONS_LIMIT: 50,
    
    // UI Settings
    MAX_DEBT_CANDIDATES_DISPLAY: 5,
    MAX_COMPLEX_FUNCTIONS_DISPLAY: 10,
    
    // Complexity Thresholds
    HIGH_COMPLEXITY_THRESHOLD: 0.6,
    LOW_IMPACT_THRESHOLD: 0.7,
    
    // ETA Calculation
    CHUNKS_PER_MINUTE: 2.8
};

export const ELEMENT_IDS = {
    // Content containers
    PROGRESS_CONTENT: 'progress-content',
    FUNCTIONS_CONTENT: 'functions-content',
    ANALYTICS_CONTENT: 'analytics-content',
    SEARCH_RESULTS: 'search-results',
    FUNCTION_TREE: 'function-tree',
    STACKTRACE_SUMMARIES: 'stacktrace-summaries',
    FUNCTION_META: 'function-meta',
    CODE: 'code',
    
    // Controls
    SEARCH_INPUT: 'search-input',
    SEARCH_BTN: 'search-btn',
    FUZZY_CHECKBOX: 'fuzzy',
    AUTO_REFRESH_SWITCH: 'auto-refresh',
    REFRESH_BTN: 'refresh-btn'
}; 