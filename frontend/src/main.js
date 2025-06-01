// Code Analysis Dashboard v2 - Refactored
import { Dashboard } from './ui/Dashboard.js';
import { ELEMENT_IDS } from './config/constants.js';
import store from './state/store.js';

console.log('Code Analysis Dashboard v2 loading...');

class App {
    constructor() {
        this.dashboard = null;
    }

    initialize() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setup());
        } else {
            this.setup();
        }
    }

    setup() {
        console.log('Dashboard ready!');
        
        // Initialize dashboard
        this.dashboard = new Dashboard();
        
        // Attach event listeners
        this.attachEventListeners();
        
        // Load initial data
        this.dashboard.load();
        
        // Set up cleanup
        this.setupCleanup();
    }

    attachEventListeners() {
        // Search functionality
        const searchInput = document.getElementById(ELEMENT_IDS.SEARCH_INPUT);
        const searchBtn = document.getElementById(ELEMENT_IDS.SEARCH_BTN);
        
        const performSearch = () => {
            const query = searchInput.value.trim();
            if (query) {
                this.dashboard.performSearch(query);
            }
        };
        
        searchBtn.addEventListener('click', performSearch);
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                performSearch();
            }
        });
        
        // Auto-refresh toggle
        const autoRefreshSwitch = document.getElementById(ELEMENT_IDS.AUTO_REFRESH_SWITCH);
        const { autoRefresh } = store.getState();
        autoRefreshSwitch.checked = autoRefresh;
        
        autoRefreshSwitch.addEventListener('sl-change', (e) => {
            store.setAutoRefresh(e.target.checked);
            
            if (e.target.checked) {
                this.dashboard.startAutoRefresh();
            } else {
                this.dashboard.stopAutoRefresh();
            }
        });
        
        // Manual refresh
        const refreshBtn = document.getElementById(ELEMENT_IDS.REFRESH_BTN);
        refreshBtn.addEventListener('click', () => {
            this.dashboard.load();
        });
        
        // Start auto-refresh if enabled
        if (autoRefresh) {
            this.dashboard.startAutoRefresh();
        }
    }

    setupCleanup() {
        // Cleanup on page unload
        window.addEventListener('beforeunload', () => {
            this.dashboard.stopAutoRefresh();
        });
    }
}

// Initialize the application
const app = new App();
app.initialize();

// Export for debugging if needed
window.__app = app;
