// Code Analysis Dashboard v2
console.log('Code Analysis Dashboard v2 loading...');

// API configuration
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// State management
let dashboardState = {
    progress: null,
    functions: [],
    searchResults: [],
    isLoading: false,
    autoRefresh: false
};

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

async function getProgress() {
    return fetchAPI('/stats/progress');
}

async function getFunctions(limit = 50) {
    return fetchAPI(`/functions?limit=${limit}&include_stats=true`);
}

async function searchCode(query) {
    const fuzzy = document.getElementById('fuzzy').checked;
    if (!query.trim()) return [];
    return fetchAPI(`/search?q=${encodeURIComponent(query)}&limit=20&fuzzy=${fuzzy}`);
}

// UI Rendering functions
function renderProgressContent(progress) {
  console.log("Render")
    const percentage = progress.total_chunks > 0 
        ? (progress.enriched_chunks / progress.total_chunks * 100).toFixed(1)
        : 0;
    
    const eta = progress.pending_chunks > 0 
        ? Math.ceil(progress.pending_chunks / 2.8) // Based on current rate
        : 0;

    // Update badge

    let badgeVariant = progress.pending_chunks === 0 ? 'success' : 'primary';
    let badgeTextContent = progress.pending_chunks === 0 ? 'Complete' : 'In Progress';

    // Update content
    document.getElementById('progress-content').innerHTML = `

        <sl-badge variant="${badgeVariant}" id="progress-badge">${badgeTextContent}</sl-badge>
        <sl-progress-bar value="${percentage}"></sl-progress-bar>
        ${eta > 0 ? `<p style="margin-top: 0.5rem; color: var(--sl-color-neutral-600);">
            <sl-icon name="info-circle-fill"></sl-icon> ETA: ~${eta} minutes
        </p>` : ''}
            <sl-card >
                <div class="metric-box">
                <sl-icon name="pie-chart-fill"></sl-icon>
                    <div class="metric-value">${percentage}%</div>
                    <div class="metric-label">Complete</div>
                </div>
            </sl-card>
            <sl-card >
                <div class="metric-box">
                <sl-icon name="clock-fill"></sl-icon>
                    <div class="metric-value">${progress.pending_chunks.toLocaleString()}</div>
                    <div class="metric-label">Remaining</div>
                </div>
            </sl-card>
            <sl-card >
                <div class="metric-box">
                    <sl-icon name="graph-up"></sl-icon>
                    <div class="metric-value">${progress.avg_complexity || 'N/A'}</div>
                    <div class="metric-label">Avg Complexity</div>
                </div>
            </sl-card>
            <sl-card >
                <div class="metric-box">
                <sl-icon name="layers-fill"></sl-icon>
                    <div class="metric-value">${progress.enriched_chunks.toLocaleString()}</div>
                    <div class="metric-label">Enriched Chunks</div>
                </div>
            
            </sl-card>
        
    `;
}

function renderTreeFromSearch(results) {
    const tree = document.getElementById('function-tree');
    if (!tree) return;

    const summaries = results.filter(r => r.type === 'function_summary');
    if (summaries.length === 0) return;

    const r = summaries[0]; // Still only showing one result

    tree.innerHTML = `
        <sl-tree-item data-function-id="${r.function_id}">
            ${r.function_name} <small style="opacity:0.6;">(${r.class_name || ''})</small>
        </sl-tree-item>
    `;

    const item = tree.querySelector('sl-tree-item');
    if (item) {
        item.addEventListener('click', () => {
            const id = item.getAttribute('data-function-id');
            loadFunctionCode(id);
        });
    }

    console.log('Rendered single tree item:', r);
}


function renderTreeFromSummaries(results) {
    const tree = document.querySelector('sl-tree');
    if (!tree) return;

    console.log(results)
    const summaries = results.filter(r => r.type === 'function_summary');
    if (summaries.length === 0) {
        tree.innerHTML = '<sl-tree-item disabled>No function summaries available</sl-tree-item>';
        return;
    }

    // Group by filepath
    const groupedByFile = summaries.reduce((acc, item) => {
        if (!acc[item.filepath]) {
            acc[item.filepath] = [];
        }
        acc[item.filepath].push(item);
        return acc;
    }, {});

    // Build the tree with all items expanded
    tree.innerHTML = Object.entries(groupedByFile).map(([filepath, items]) => {
        const children = items.map(r => `
            <sl-tree-item data-function-id="${r.function_id}">
                ${r.function_name}
                ${r.class_name ? `<small style="opacity:0.6;">(${r.class_name})</small>` : ''}
            </sl-tree-item>
        `).join('');

        return `
            <sl-tree-item expanded>
                <span style="font-size: 0.85rem; font-weight: 600; color: var(--sl-color-gray-600);">
                    ${filepath}
                </span>
                ${children}
            </sl-tree-item>
        `;
    }).join('');

    // Click binding
    tree.querySelectorAll('sl-tree-item[data-function-id]').forEach(item => {
        item.addEventListener('click', () => {
            const id = item.getAttribute('data-function-id');
            loadFunctionCode(id);
        });
    });

    console.log('Fully expanded tree with grouped summaries rendered.');
}



async function analyzeStacktrace(rawStacktrace) {
    return fetchAPI('/analyze', {
        method: 'POST',
        body: JSON.stringify({ stacktrace: rawStacktrace }),
    });
}


async function loadFunctionCode(functionId) {
    try {
        const response = await fetchAPI(`/code/${functionId}`);
        const { code, start_line, end_line, function_name, parameters } = response;
        let virtStart_line = start_line +0 
        window.currentStartLine = virtStart_line;
        console.log("start_line", virtStart_line)

        let parsedParams;
        try {
            parsedParams = JSON.parse(parameters);
        } catch (e) {
            console.warn('Parameter parsing failed:', e);
            parsedParams = [];
        }

        const paramStr = Array.isArray(parsedParams)
            ? parsedParams.map(p => `${p.name}${p.default !== undefined ? ` = ${p.default}` : ''}`).join(', ')
            : '—';

        // Inject metadata
        const metaContainer = document.getElementById('function-meta');
        if (metaContainer) {
            metaContainer.innerHTML = `
                <strong>${function_name}(${paramStr})</strong><br>
                <sl-badge variant="neutral">Lines: ${virtStart_line}–${end_line}</sl-badge>
            `;
        }
        // Insert code text
        const functionHeader= function_name + "(" +paramStr + ") ";
        const codeContainer = document.querySelector('#code pre code');
        codeContainer.textContent = functionHeader+ code || '// No source code found';

        // Set PHP class and re-highlight
        delete codeContainer.dataset.highlighted;
        codeContainer.className = 'php';
        hljs.highlightElement(codeContainer);

        // Add line numbers, starting from correct base
        hljs.lineNumbersBlock(codeContainer, {
            startFrom: virtStart_line || 0
        });
        // Parse parameters (stringified JSON)


    } catch (err) {
        console.error('Failed to load code:', err);
    }
}





function renderSearchResults(results) {
    const resultsContainer = document.getElementById('search-results');
    
    if (!results || results.length === 0) {
        resultsContainer.innerHTML = '<div class="empty-state">No results found. Try different search terms.</div>';
        return;
    }
    resultsContainer.innerHTML = `
        <div class="results-header">
            <h3>Found ${results.length} results:</h3>
        </div>
        <div class="results-list">
            ${results.map(result => `
                <sl-card 
                  class="result-item" 
                  data-function-id="${result.function_id}" 
                  data-start-line="${result.start_line}" 
                  data-end-line="${result.end_line}">
                    <div class="result-header">
                        <div class="result-title">
                            <sl-icon name="code-slash"></sl-icon>
                            <strong>${result.function_name}</strong>
                            ${result.class_name ? `<sl-tag size="small">${result.class_name}</sl-tag>` : ''}
                        </div>
                        <div class="result-scores">
                            <sl-badge variant="neutral">SL: ${result.start_line}</sl-badge>
                            <sl-badge variant="neutral">EL: ${result.end_line}</sl-badge>
                            <sl-badge variant="neutral">C: ${result.complexity_score?.toFixed(2) || 'N/A'}</sl-badge>
                            <sl-badge variant="primary">I: ${result.business_impact_score?.toFixed(2) || 'N/A'}</sl-badge>
                        </div>
                    </div>
                    <div class="result-content">
                        <p><strong>File:</strong> <code>${result.filepath}</code></p>
                        <p><strong>Summary:</strong> ${result.summary}</p>
                    </div>
                </sl-card>
            `).join('')}
        </div>
    `;
      document.querySelectorAll('.result-item').forEach(card => {
          card.addEventListener('click', () => {
              const start = parseInt(card.dataset.startLine, 10);
              const end = parseInt(card.dataset.endLine, 10);
              document.querySelectorAll('.result-item').forEach(el =>
                  el.classList.remove('selected-summary')
              );
              card.classList.add('selected-summary');

              highlightCodeLines(start, end);
              scrollToLine(start);
          });
      });


}



function highlightCodeLines(start, end) {
    clearHighlightedLines();

    document.querySelectorAll('.hljs-ln tr').forEach((row, index) => {
        const lineNumber = (index + currentStartLine) ; // Use tracked start_line from function load
        if (lineNumber >= start && lineNumber <= end) {
            row.classList.add('highlighted-line');
        }
    });
}

function clearHighlightedLines() {
    document.querySelectorAll('.hljs-ln tr.highlighted-line')
        .forEach(row => row.classList.remove('highlighted-line'));
}

function scrollToLine(lineNumber) {
    const index = lineNumber - currentStartLine;
    const rows = document.querySelectorAll('.hljs-ln tr');
    const row = rows[index];
    if (row) {
        row.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}

function renderFunctionsContent(functions) {
    const topComplex = functions
        .filter(f => f.avg_complexity > 0)
        .sort((a, b) => b.avg_complexity - a.avg_complexity)
        .slice(0, 10);

    const container = document.getElementById('functions-content');

    if (topComplex.length === 0) {
        container.innerHTML = '<div class="empty-state">No complex functions found yet. Enrichment in progress...</div>';
        return;
    }

    container.innerHTML = `
        <div class="functions-list">
            ${topComplex.map(func => `
                <div class="function-item">
                    <div class="function-info">
                        <div class="function-name">
                            <sl-icon name="braces"></sl-icon>
                            <strong>${func.function_name}</strong>
                            ${func.class_name ? `<sl-tag size="small">${func.class_name}</sl-tag>` : ''}
                        </div>
                        <div class="function-path">
                            <code>${func.filepath}</code>
                        </div>
                    </div>
                    <div class="function-metrics">
                        <sl-badge variant="warning">
                            Complexity: ${func.avg_complexity.toFixed(2)}
                        </sl-badge>
                        ${func.avg_impact ? `
                            <sl-badge variant="primary">
                                Impact: ${func.avg_impact.toFixed(2)}
                            </sl-badge>
                        ` : ''}
                    </div>
                </div>
            `).join('')}
        </div>
    `;
}

function renderAnalyticsContent(functions) {
    const enriched = functions.filter(f => f.avg_complexity > 0 && f.avg_impact > 0);
    const highComplexLowImpact = enriched.filter(f => f.avg_complexity > 0.6 && f.avg_impact < 0.7);
    
    const container = document.getElementById('analytics-content');

    if (highComplexLowImpact.length > 0) {
        container.innerHTML = `
            <sl-alert variant="warning" open>
                <sl-icon slot="icon" name="exclamation-triangle-fill"></sl-icon>
                Found ${highComplexLowImpact.length} potential technical debt candidates
            </sl-alert>
            
            <div class="debt-candidates">
                ${highComplexLowImpact.slice(0, 5).map(func => `
                    <div class="debt-item">
                        <div class="debt-info">
                            <strong>${func.function_name}</strong>
                            <code>${func.filepath}</code>
                        </div>
                        <div class="debt-scores">
                            <sl-badge variant="warning">High Complexity: ${func.avg_complexity.toFixed(2)}</sl-badge>
                            <sl-badge variant="neutral">Low Impact: ${func.avg_impact.toFixed(2)}</sl-badge>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    } else {
        container.innerHTML = `
            <sl-alert variant="success" open>
                <sl-icon slot="icon" name="check-circle-fill"></sl-icon>
                No obvious technical debt candidates found. Good job! 🎉
            </sl-alert>
        `;
    }
}

// Main app logic
async function loadDashboard() {
    if (dashboardState.isLoading) return;
    
    dashboardState.isLoading = true;
    showLoadingStates();
    
    try {
        // Load data in parallel
        const [progress, functions] = await Promise.all([
            getProgress(),
            getFunctions()
        ]);
        
        dashboardState.progress = progress;
        dashboardState.functions = functions;
        
        // Render all components
    //
        renderProgressContent(progress);
        renderFunctionsContent(functions);
        renderAnalyticsContent(functions);
        
    } catch (error) {
        console.error('Failed to load dashboard:', error);
        showError('Failed to load dashboard data. Make sure the API is running.');
    } finally {
        dashboardState.isLoading = false;
    }
}

function showLoadingStates() {
    const loadingHTML = '<div class="loading"><sl-spinner></sl-spinner>Loading...</div>';
    
    document.getElementById('progress-content').innerHTML = loadingHTML;
    document.getElementById('functions-content').innerHTML = loadingHTML;
    document.getElementById('analytics-content').innerHTML = loadingHTML;
}

function showError(message) {
    const errorHTML = `
        <sl-alert variant="danger" open>
            <sl-icon slot="icon" name="exclamation-octagon-fill"></sl-icon>
            <strong>Error:</strong> ${message}
            <sl-button slot="action" variant="text" size="small" onclick="loadDashboard()">
                Retry
            </sl-button>
        </sl-alert>
    `;
    
    document.getElementById('progress-content').innerHTML = errorHTML;
    document.getElementById('functions-content').innerHTML = errorHTML;
    document.getElementById('analytics-content').innerHTML = errorHTML;
}



function renderStacktraceSummaries(summaries) {
    const container = document.getElementById('stacktrace-summaries');
    if (!container) return;

    if (!summaries || summaries.length === 0) {
        container.innerHTML = '<div class="empty-state">No stacktrace summaries available.</div>';
        return;
    }

    container.innerHTML = `
        <div class="stacktrace-summary-list">
            ${summaries.map((s, idx) => `
                <sl-alert 
                    variant="${s.startsWith('✅') ? 'success' : 'danger'}" 
                    open 
                    class="stacktrace-summary-item">
                    <sl-icon slot="icon" name="${s.startsWith('✅') ? 'check-lg' : 'exclamation-triangle-fill'}"></sl-icon>
                    ${s}
                </sl-alert>
            `).join('')}
        </div>
    `;
}


// Event handlers
function attachEventListeners() {
    // Search functionality
    const searchInput = document.getElementById('search-input');
    const searchBtn = document.getElementById('search-btn');
    
    async function performHybridQuery() {
        const input = searchInput.value.trim();
        if (!input) return;

        searchBtn.loading = true;

        try {
            if (input.includes('::')) {
                // Stacktrace style: Analyze
                const results = await analyzeStacktrace(input);
console.log('Stacktrace analysis response:', results);
                dashboardState.searchResults = results;

                const summaries = results.filter(r => r.type === "function_summary" || r.type === "error");
                const related = results.filter(r => r.type === "chunk");

                dashboardState.stackSummaries = summaries;

                renderStacktraceSummaries(summaries);
                renderSearchResults(related);
                renderTreeFromSummaries(results.filter(r => r.type === 'function_summary'));
            } else {
                // Plain search
                const results = await searchCode(input);
                dashboardState.searchResults = results;
                console.log('Stacktrace analysis response:', results);

                renderSearchResults(results);
                renderTreeFromSearch(results.filter(r => r.type === 'chunk')); // optional
            }
        } catch (error) {
            console.error('Search/Analysis failed:', error);
            document.getElementById('search-results').innerHTML =
                '<sl-alert variant="danger" open><sl-icon slot="icon" name="exclamation-triangle-fill"></sl-icon>Search failed. Please try again.</sl-alert>';
        } finally {
            searchBtn.loading = false;
        }
    }
    
    searchBtn.addEventListener('click', performHybridQuery);
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            performHybridQuery();
        }
    });
    
    // Auto-refresh toggle
    const autoRefreshSwitch = document.getElementById('auto-refresh');
    autoRefreshSwitch.checked = dashboardState.autoRefresh;
    autoRefreshSwitch.addEventListener('sl-change', (e) => {
        dashboardState.autoRefresh = e.target.checked;
        if (dashboardState.autoRefresh) {
            startAutoRefresh();
        }
    });
    
    // Manual refresh
    const refreshBtn = document.getElementById('refresh-btn');
    refreshBtn.addEventListener('click', loadDashboard);
    
    // Start auto-refresh if enabled
    if (dashboardState.autoRefresh) {
        startAutoRefresh();
    }
}

function startAutoRefresh() {
    // Clear any existing interval
    if (window.dashboardInterval) {
        clearInterval(window.dashboardInterval);
    }
    
    window.dashboardInterval = setInterval(() => {
        if (dashboardState.autoRefresh && !dashboardState.isLoading) {
            loadDashboard();
        }
    }, 30000); // 30 seconds
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('Dashboard ready!');
    attachEventListeners();
    loadDashboard();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.dashboardInterval) {
        clearInterval(window.dashboardInterval);
    }
});
