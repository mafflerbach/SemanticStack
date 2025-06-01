export function renderFunctionsContent(functions) {
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