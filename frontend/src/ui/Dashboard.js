// Dashboard UI Orchestrator
import { 
    ProgressCard, 
    FunctionsList, 
    AnalyticsCard, 
    SearchResults, 
    FunctionTree, 
    CodeViewer, 
    StacktraceSummaries 
} from './components/index.js';
import { isStacktraceInput } from '../utils/helpers.js';
import { CONFIG, ELEMENT_IDS } from '../config/constants.js';
import store from '../state/store.js';
import api from '../api/client.js';

export class Dashboard {
    constructor() {
        this.initializeComponents();
        this.autoRefreshInterval = null;
    }

    initializeComponents() {
        // Initialize all UI components with null checks
        const progressElement = document.getElementById(ELEMENT_IDS.PROGRESS_CONTENT);
        const functionsElement = document.getElementById(ELEMENT_IDS.FUNCTIONS_CONTENT);
        const analyticsElement = document.getElementById(ELEMENT_IDS.ANALYTICS_CONTENT);
        const searchResultsElement = document.getElementById(ELEMENT_IDS.SEARCH_RESULTS);
        const functionTreeElement = document.getElementById(ELEMENT_IDS.FUNCTION_TREE);
        const stacktraceSummariesElement = document.getElementById(ELEMENT_IDS.STACKTRACE_SUMMARIES);
        const functionMetaElement = document.getElementById(ELEMENT_IDS.FUNCTION_META);
        const codeElement = document.getElementById(ELEMENT_IDS.CODE);

        // Create components only if elements exist
        this.progressCard = progressElement ? new ProgressCard(progressElement) : null;
        this.functionsList = functionsElement ? new FunctionsList(functionsElement) : null;
        this.analyticsCard = analyticsElement ? new AnalyticsCard(analyticsElement) : null;
        this.searchResults = searchResultsElement ? new SearchResults(searchResultsElement) : null;
        this.functionTree = functionTreeElement ? new FunctionTree(functionTreeElement) : null;
        this.stacktraceSummaries = stacktraceSummariesElement ? new StacktraceSummaries(stacktraceSummariesElement) : null;
        
        if (functionMetaElement && codeElement) {
            this.codeViewer = new CodeViewer(functionMetaElement, codeElement);
        } else {
            this.codeViewer = null;
        }

        // Log warnings for missing elements
        if (!progressElement) console.warn(`Element not found: ${ELEMENT_IDS.PROGRESS_CONTENT}`);
        if (!functionsElement) console.warn(`Element not found: ${ELEMENT_IDS.FUNCTIONS_CONTENT}`);
        if (!analyticsElement) console.warn(`Element not found: ${ELEMENT_IDS.ANALYTICS_CONTENT}`);
        if (!searchResultsElement) console.warn(`Element not found: ${ELEMENT_IDS.SEARCH_RESULTS}`);
        if (!functionTreeElement) console.warn(`Element not found: ${ELEMENT_IDS.FUNCTION_TREE}`);
        if (!stacktraceSummariesElement) console.warn(`Element not found: ${ELEMENT_IDS.STACKTRACE_SUMMARIES}`);
        if (!functionMetaElement) console.warn(`Element not found: ${ELEMENT_IDS.FUNCTION_META}`);
        if (!codeElement) console.warn(`Element not found: ${ELEMENT_IDS.CODE}`);

        // Set up component interactions
        this.setupComponentInteractions();
    }

    setupComponentInteractions() {
        // Search results click -> highlight code
        if (this.searchResults && this.codeViewer) {
            this.searchResults.onLineSelect((start, end) => {
                this.codeViewer.highlightLines(start, end);
            });
        }

        // Function tree click -> load function code
        if (this.functionTree) {
            this.functionTree.onSelect(async (functionId) => {
                await this.loadFunctionCode(functionId);
            });
        }
    }

    async load() {
        const state = store.getState();
        if (state.isLoading) return;
        
        store.setLoading(true);
        this.showLoadingStates();
        
        try {
            // Load data in parallel
            const [progress, functions] = await Promise.all([
                api.getProgress(),
                api.getFunctions()
            ]);
            
            store.setProgress(progress);
            store.setFunctions(functions);
            
            // Render all components that exist
            if (this.progressCard) this.progressCard.render(progress);
            if (this.functionsList) this.functionsList.render(functions);
            if (this.analyticsCard) this.analyticsCard.render(functions);
            
        } catch (error) {
            console.error('Failed to load dashboard:', error);
            this.showError('Failed to load dashboard data. Make sure the API is running.');
        } finally {
            store.setLoading(false);
        }
    }

    async performSearch(query) {
        if (!query.trim()) return;

        const searchBtn = document.getElementById(ELEMENT_IDS.SEARCH_BTN);
        if (searchBtn) searchBtn.loading = true;

        try {
            if (isStacktraceInput(query)) {
                // Stacktrace analysis
                const results = await api.analyzeStacktrace(query);
                store.setSearchResults(results);

                const summaries = results.filter(r => r.type === "function_summary" || r.type === "error");
                const related = results.filter(r => r.type === "chunk");

                store.setStackSummaries(summaries);
                
                if (this.stacktraceSummaries) this.stacktraceSummaries.render(summaries);
                if (this.searchResults) this.searchResults.render(related);
                if (this.functionTree) this.functionTree.renderFromSummaries(results.filter(r => r.type === 'function_summary'));
            } else {
                // Regular search
                const fuzzyCheckbox = document.getElementById(ELEMENT_IDS.FUZZY_CHECKBOX);
                const fuzzy = fuzzyCheckbox ? fuzzyCheckbox.checked : false;
                const results = await api.searchCode(query, fuzzy);
                
                store.setSearchResults(results);
                if (this.searchResults) this.searchResults.render(results);
                if (this.functionTree) this.functionTree.renderFromSearch(results.filter(r => r.type === 'chunk'));
            }
        } catch (error) {
            console.error('Search/Analysis failed:', error);
            if (this.searchResults) this.searchResults.renderError('Search failed. Please try again.');
        } finally {
            if (searchBtn) searchBtn.loading = false;
        }
    }

    async loadFunctionCode(functionId) {
        if (!this.codeViewer) {
            console.warn('CodeViewer not initialized - missing required elements');
            return;
        }

        try {
            const functionData = await api.getFunctionCode(functionId);
            await this.codeViewer.displayFunction(functionData);
        } catch (err) {
            console.error('Failed to load code:', err);
        }
    }

    showLoadingStates() {
        if (this.progressCard) this.progressCard.renderLoading();
        if (this.functionsList) this.functionsList.renderLoading();
        if (this.analyticsCard) this.analyticsCard.renderLoading();
    }

    showError(message) {
        if (this.progressCard) this.progressCard.renderError(message);
        if (this.functionsList) this.functionsList.renderError(message);
        if (this.analyticsCard) this.analyticsCard.renderError(message);
    }

    startAutoRefresh() {
        // Clear any existing interval
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
        }
        
        this.autoRefreshInterval = setInterval(() => {
            const { autoRefresh, isLoading } = store.getState();
            if (autoRefresh && !isLoading) {
                this.load();
            }
        }, CONFIG.AUTO_REFRESH_INTERVAL);
    }

    stopAutoRefresh() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
            this.autoRefreshInterval = null;
        }
    }
} 