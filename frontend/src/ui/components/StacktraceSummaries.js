// Stacktrace Summaries Component
export class StacktraceSummaries {
    constructor(container) {
        this.container = container;
    }

    render(summaries) {
        // Check if container exists
        if (!this.container) {
            console.warn('StacktraceSummaries: Container element not found');
            return;
        }

        if (!summaries || summaries.length === 0) {
            this.renderEmpty();
            return;
        }

        this.container.innerHTML = `
            <div class="stacktrace-summary-list">
                ${summaries.map((summary, idx) => this.renderSummaryItem(summary)).join('')}
            </div>
        `;
    }

    renderSummaryItem(summary) {
        // Handle both string summaries and object summaries
        let summaryText = '';
        let isSuccess = false;
        
        if (typeof summary === 'string') {
            // Legacy string format
            summaryText = summary;
            isSuccess = summary.startsWith('✅');
        } else if (summary && typeof summary === 'object') {
            // Object format from API
            if (summary.type === 'error') {
                summaryText = summary.message || summary.summary || 'Error occurred';
                isSuccess = false;
            } else if (summary.type === 'function_summary') {
                // Format function summary
                summaryText = `✅ Found function: ${summary.function_name} in ${summary.filepath}`;
                isSuccess = true;
            } else {
                // Fallback for other object types
                summaryText = summary.summary || summary.message || JSON.stringify(summary);
                isSuccess = summary.type !== 'error';
            }
        }

        const variant = isSuccess ? 'success' : 'danger';
        const icon = isSuccess ? 'check-lg' : 'exclamation-triangle-fill';

        return `
            <sl-alert 
                variant="${variant}" 
                open 
                class="stacktrace-summary-item">
                <sl-icon slot="icon" name="${icon}"></sl-icon>
                ${summaryText}
            </sl-alert>
        `;
    }

    renderEmpty() {
        if (!this.container) return;
        this.container.innerHTML = '<div class="empty-state">No stacktrace summaries available.</div>';
    }

    clear() {
        if (!this.container) return;
        this.container.innerHTML = '';
    }
} 