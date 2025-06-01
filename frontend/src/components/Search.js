import { searchCode, analyzeStacktrace } from '../api.js';
import { dashboardState, setSearchResults, setStackSummaries } from '../store.js';
import { renderTreeFromSearch, renderTreeFromSummaries } from './Tree.js';

export function renderSearchResults(results) {
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

    attachSearchResultListeners();
}

function attachSearchResultListeners() {
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

function clearHighlightedLines() {
    document.querySelectorAll('.hljs-ln tr.highlighted-line')
        .forEach(row => row.classList.remove('highlighted-line'));
}

function highlightCodeLines(start, end) {
    clearHighlightedLines();

    document.querySelectorAll('.hljs-ln tr').forEach((row, index) => {
        const lineNumber = (index + window.currentStartLine) ; // Use tracked start_line from function load
        if (lineNumber >= start && lineNumber <= end) {
            row.classList.add('highlighted-line');
        }
    });
}


function scrollToLine(lineNumber) {
    const index = lineNumber - window.currentStartLine;
    const rows = document.querySelectorAll('.hljs-ln tr');
    const row = rows[index];
    if (row) {
        row.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}

export async function performHybridQuery(input, searchBtn) {
    if (!input) return;

    searchBtn.loading = true;

    try {
        if (input.includes('::')) {
            // Stacktrace style: Analyze
            const results = await analyzeStacktrace(input);
            setSearchResults(results);

            const summaries = results.filter(r => r.type === "function_summary" || r.type === "error");
            const related = results.filter(r => r.type === "chunk");

            setStackSummaries(summaries);

            renderStacktraceSummaries(summaries);
            renderSearchResults(related);
            renderTreeFromSummaries(results.filter(r => r.type === 'function_summary'));
        } else {
            // Plain search
            const fuzzy = document.getElementById('fuzzy').checked;
            const results = await searchCode(input, fuzzy);
            setSearchResults(results);

            renderSearchResults(results);
            renderTreeFromSearch(results.filter(r => r.type === 'chunk'));
        }
    } catch (error) {
        console.error('Search/Analysis failed:', error);
        document.getElementById('search-results').innerHTML =
            '<sl-alert variant="danger" open><sl-icon slot="icon" name="exclamation-triangle-fill"></sl-icon>Search failed. Please try again.</sl-alert>';
    } finally {
        searchBtn.loading = false;
    }
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

