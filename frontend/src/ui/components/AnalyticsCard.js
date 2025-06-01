// Analytics Card Component
import { filterHighComplexLowImpact } from '../../utils/helpers.js';
import { CONFIG } from '../../config/constants.js';

export class AnalyticsCard {
    constructor(container) {
        this.container = container;
    }

    render(functions) {
        const debtCandidates = filterHighComplexLowImpact(functions);

        if (debtCandidates.length > 0) {
            this.renderDebtCandidates(debtCandidates);
        } else {
            this.renderNoDebt();
        }
    }

    renderDebtCandidates(candidates) {
        this.container.innerHTML = `
            <sl-alert variant="warning" open>
                <sl-icon slot="icon" name="exclamation-triangle-fill"></sl-icon>
                Found ${candidates.length} potential technical debt candidates
            </sl-alert>
            
            <div class="debt-candidates">
                ${candidates.slice(0, CONFIG.MAX_DEBT_CANDIDATES_DISPLAY).map(func => this.renderDebtItem(func)).join('')}
            </div>
        `;
    }

    renderDebtItem(func) {
        return `
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
        `;
    }

    renderNoDebt() {
        this.container.innerHTML = `
            <sl-alert variant="success" open>
                <sl-icon slot="icon" name="check-circle-fill"></sl-icon>
                No obvious technical debt candidates found. Good job! 🎉
            </sl-alert>
        `;
    }

    renderLoading() {
        this.container.innerHTML = '<div class="loading"><sl-spinner></sl-spinner>Loading...</div>';
    }

    renderError(message) {
        this.container.innerHTML = `
            <sl-alert variant="danger" open>
                <sl-icon slot="icon" name="exclamation-octagon-fill"></sl-icon>
                <strong>Error:</strong> ${message}
            </sl-alert>
        `;
    }
} 