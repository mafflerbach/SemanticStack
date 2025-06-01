// Search Results Component
import store from '../../state/store.js';

export class SearchResults {
    constructor(container) {
        this.container = container;
        this.selectedCard = null;
        this.lineSelectCallback = null;
    }

    render(results) {
        if (!results || results.length === 0) {
            this.renderEmpty();
            return;
        }

        this.container.innerHTML = `
            <div class="results-header">
                <h3>Found ${results.length} results:</h3>
            </div>
            <div class="results-list">
                ${results.map(result => this.renderResultCard(result)).join('')}
            </div>
        `;

        this.attachEventListeners();
    }

    renderResultCard(result) {
        return `
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
        `;
    }

    attachEventListeners() {
        this.container.querySelectorAll('.result-item').forEach(card => {
            card.addEventListener('click', () => this.handleCardClick(card));
        });
    }

    handleCardClick(card) {
        const start = parseInt(card.dataset.startLine, 10);
        const end = parseInt(card.dataset.endLine, 10);
        
        // Remove previous selection
        if (this.selectedCard) {
            this.selectedCard.classList.remove('selected-summary');
        }
        
        // Add new selection
        card.classList.add('selected-summary');
        this.selectedCard = card;

        // Emit events for code highlighting
        if (this.lineSelectCallback) {
            this.lineSelectCallback(start, end);
        }
    }

    renderEmpty() {
        this.container.innerHTML = '<div class="empty-state">No results found. Try different search terms.</div>';
    }

    renderError(message) {
        this.container.innerHTML = `
            <sl-alert variant="danger" open>
                <sl-icon slot="icon" name="exclamation-octagon-fill"></sl-icon>
                <strong>Error:</strong> ${message}
            </sl-alert>
        `;
    }

    onLineSelect(callback) {
        this.lineSelectCallback = callback;
    }
} 