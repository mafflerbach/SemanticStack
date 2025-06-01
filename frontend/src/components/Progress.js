export function renderProgressContent(progress) {
    const percentage = progress.total_chunks > 0 
        ? (progress.enriched_chunks / progress.total_chunks * 100).toFixed(1)
        : 0;
    
    const eta = progress.pending_chunks > 0 
        ? Math.ceil(progress.pending_chunks / 2.8) // Based on current rate
        : 0;

    let badgeVariant = progress.pending_chunks === 0 ? 'success' : 'primary';
    let badgeTextContent = progress.pending_chunks === 0 ? 'Complete' : 'In Progress';

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