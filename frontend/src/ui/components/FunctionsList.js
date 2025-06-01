// Functions List Component
import { getTopComplexFunctions } from '../../utils/helpers.js';

export class FunctionsList {
    constructor(container) {
        this.container = container;
    }

    render(functions) {
        const topComplex = getTopComplexFunctions(functions, 10);

        if (topComplex.length === 0) {
            this.renderEmpty();
            return;
        }

        this.container.innerHTML = `
            <div class="functions-list">
                ${topComplex.map(func => this.renderFunctionItem(func)).join('')}
            </div>
        `;
    }

    renderFunctionItem(func) {
        return `
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
        `;
    }

    renderEmpty() {
        this.container.innerHTML = '<div class="empty-state">No complex functions found yet. Enrichment in progress...</div>';
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