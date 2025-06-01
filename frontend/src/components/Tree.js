import { loadFunctionCode } from './Code.js';

export function renderTreeFromSearch(results) {
    const tree = document.getElementById('function-tree');
    if (!tree) return;

    const summaries = results.filter(r => r.type === 'function_summary');
    if (summaries.length === 0) return;

    const r = summaries[0]; // Still only showing one result

    tree.innerHTML = `
        <sl-tree-item data-function-id="${r.function_id}">
            ${r.function_name} <small style="opacity:0.6;">(${r.class_name || ''})</small>
        </sl-tree-item>
    `;

    attachTreeItemListeners(tree);
}

export function renderTreeFromSummaries(results) {
    const tree = document.querySelector('sl-tree');
    if (!tree) return;

    const summaries = results.filter(r => r.type === 'function_summary');
    if (summaries.length === 0) {
        tree.innerHTML = '<sl-tree-item disabled>No function summaries available</sl-tree-item>';
        return;
    }

    // Group by filepath
    const groupedByFile = summaries.reduce((acc, item) => {
        if (!acc[item.filepath]) {
            acc[item.filepath] = [];
        }
        acc[item.filepath].push(item);
        return acc;
    }, {});

    // Build the tree with all items expanded
    tree.innerHTML = Object.entries(groupedByFile).map(([filepath, items]) => {
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
    }).join('');

    attachTreeItemListeners(tree);
}

function attachTreeItemListeners(tree) {
    tree.querySelectorAll('sl-tree-item[data-function-id]').forEach(item => {
        item.addEventListener('click', () => {
            const id = item.getAttribute('data-function-id');
            loadFunctionCode(id);
        });
    });
} 