export function renderAnalyticsContent(functions) {
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