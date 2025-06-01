// State Management Module
class Store {
    constructor() {
        this.state = {
            progress: null,
            functions: [],
            searchResults: [],
            stackSummaries: [],
            isLoading: false,
            autoRefresh: false,
            currentFunction: null,
            currentStartLine: 0
        };
        
        this.subscribers = new Set();
    }

    // Get current state
    getState() {
        return { ...this.state };
    }

    // Update state and notify subscribers
    setState(updates) {
        this.state = { ...this.state, ...updates };
        this.notify();
    }

    // Subscribe to state changes
    subscribe(callback) {
        this.subscribers.add(callback);
        return () => this.subscribers.delete(callback);
    }

    // Notify all subscribers
    notify() {
        this.subscribers.forEach(callback => callback(this.state));
    }

    // Convenience methods
    setLoading(isLoading) {
        this.setState({ isLoading });
    }

    setProgress(progress) {
        this.setState({ progress });
    }

    setFunctions(functions) {
        this.setState({ functions });
    }

    setSearchResults(searchResults) {
        this.setState({ searchResults });
    }

    setStackSummaries(stackSummaries) {
        this.setState({ stackSummaries });
    }

    setAutoRefresh(autoRefresh) {
        this.setState({ autoRefresh });
    }

    setCurrentFunction(currentFunction, currentStartLine) {
        this.setState({ currentFunction, currentStartLine });
    }
}

export default new Store(); 