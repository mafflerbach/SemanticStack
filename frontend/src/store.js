// State management
export const dashboardState = {
    progress: null,
    functions: [],
    searchResults: [],
    isLoading: false,
    autoRefresh: false,
    stackSummaries: [],
    currentStartLine: 0
};

// State update functions
export function setProgress(progress) {
    dashboardState.progress = progress;
}

export function setFunctions(functions) {
    dashboardState.functions = functions;
}

export function setSearchResults(results) {
    dashboardState.searchResults = results;
}

export function setLoading(isLoading) {
    dashboardState.isLoading = isLoading;
}

export function setAutoRefresh(autoRefresh) {
    dashboardState.autoRefresh = autoRefresh;
}

export function setStackSummaries(summaries) {
    dashboardState.stackSummaries = summaries;
}

export function setCurrentStartLine(line) {
    dashboardState.currentStartLine = line;
} 