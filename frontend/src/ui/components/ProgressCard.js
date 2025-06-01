// Progress Card Component
import { calculateProgress } from '../../utils/helpers.js';

export class ProgressCard {
    constructor(container) {
        this.container = container;
    }

    render(progress) {
        if (!progress) {
            this.renderLoading();
            return;
        }

        const { percentage, eta } = calculateProgress(progress);
        const badgeVariant = progress.pending_chunks === 0 ? 'success' : 'primary';
        const badgeTextContent = progress.pending_chunks === 0 ? 'Complete' : 'In Progress';

        this.container.innerHTML = `
            <sl-badge variant="${badgeVariant}" id="progress-badge">${badgeTextContent}</sl-badge>
            <sl-progress-bar value="${percentage}"></sl-progress-bar>
            ${eta > 0 ? `<p style="margin-top: 0.5rem; color: var(--sl-color-neutral-600);">
                <sl-icon name="info-circle-fill"></sl-icon> ETA: ~${eta} minutes
            </p>` : ''}
            ${this.renderMetrics(progress, percentage)}
        `;
    }

    renderMetrics(progress, percentage) {
        return `
            <sl-card>
                <div class="metric-box">
                    <sl-icon name="pie-chart-fill"></sl-icon>
                    <div class="metric-value">${percentage}%</div>
                    <div class="metric-label">Complete</div>
                </div>
            </sl-card>
            <sl-card>
                <div class="metric-box">
                    <sl-icon name="clock-fill"></sl-icon>
                    <div class="metric-value">${progress.pending_chunks.toLocaleString()}</div>
                    <div class="metric-label">Remaining</div>
                </div>
            </sl-card>
            <sl-card>
                <div class="metric-box">
                    <sl-icon name="graph-up"></sl-icon>
                    <div class="metric-value">${progress.avg_complexity || 'N/A'}</div>
                    <div class="metric-label">Avg Complexity</div>
                </div>
            </sl-card>
            <sl-card>
                <div class="metric-box">
                    <sl-icon name="layers-fill"></sl-icon>
                    <div class="metric-value">${progress.enriched_chunks.toLocaleString()}</div>
                    <div class="metric-label">Enriched Chunks</div>
                </div>
            </sl-card>
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