// Function Tree Component
import { groupByFilepath } from '../../utils/helpers.js';

export class FunctionTree {
    constructor(container) {
        this.container = container;
        this.onFunctionSelect = null;
    }

    renderFromSearch(results) {
        const summaries = results.filter(r => r.type === 'function_summary');
        if (summaries.length === 0) return;

        const r = summaries[0]; // Still only showing one result

        this.container.innerHTML = `
            <sl-tree-item data-function-id="${r.function_id}">
                ${r.function_name} <small style="opacity:0.6;">(${r.class_name || ''})</small>
            </sl-tree-item>
        `;

        this.attachEventListeners();
    }

    renderFromSummaries(results) {
        const summaries = results.filter(r => r.type === 'function_summary');
        
        if (summaries.length === 0) {
            this.renderEmpty();
            return;
        }

        const groupedByFile = groupByFilepath(summaries);

        this.container.innerHTML = Object.entries(groupedByFile)
            .map(([filepath, items]) => this.renderFileGroup(filepath, items))
            .join('');

        this.attachEventListeners();
    }

    renderFileGroup(filepath, items) {
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
    }

    attachEventListeners() {
        this.container.querySelectorAll('sl-tree-item[data-function-id]').forEach(item => {
            item.addEventListener('click', () => {
                const id = item.getAttribute('data-function-id');
                this.onFunctionSelect?.(id);
            });
        });
    }

    renderEmpty() {
        this.container.innerHTML = '<sl-tree-item disabled>No function summaries available</sl-tree-item>';
    }

    onSelect(callback) {
        this.onFunctionSelect = callback;
    }
} 