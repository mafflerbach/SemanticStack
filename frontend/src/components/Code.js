import { getFunctionCode } from '../api.js';
import { dashboardState, setCurrentStartLine } from '../store.js';

export async function loadFunctionCode(functionId) {
    try {
        const response = await getFunctionCode(functionId);
        const { code, start_line, end_line, function_name, parameters } = response;
        let virtStart_line = start_line + 0;
        setCurrentStartLine(virtStart_line);

        let parsedParams;
        try {
            parsedParams = JSON.parse(parameters);
        } catch (e) {
            console.warn('Parameter parsing failed:', e);
            parsedParams = [];
        }

        const paramStr = Array.isArray(parsedParams)
            ? parsedParams.map(p => `${p.name}${p.default !== undefined ? ` = ${p.default}` : ''}`).join(', ')
            : '—';

        // Inject metadata
        const metaContainer = document.getElementById('function-meta');
        if (metaContainer) {
            metaContainer.innerHTML = `
                <strong>${function_name}(${paramStr})</strong><br>
                <sl-badge variant="neutral">Lines: ${virtStart_line}–${end_line}</sl-badge>
            `;
        }

        // Insert code text
        const functionHeader = function_name + "(" + paramStr + ") ";
        const codeContainer = document.querySelector('#code pre code');
        codeContainer.textContent = functionHeader + code || '// No source code found';

        // Set PHP class and re-highlight
        delete codeContainer.dataset.highlighted;
        codeContainer.className = 'php';
        hljs.highlightElement(codeContainer);

        // Add line numbers, starting from correct base
        hljs.lineNumbersBlock(codeContainer, {
            startFrom: virtStart_line || 0
        });

    } catch (err) {
        console.error('Failed to load code:', err);
    }
}

export function highlightCodeLines(start, end) {
    clearHighlightedLines();

    document.querySelectorAll('.hljs-ln tr').forEach((row, index) => {
        const lineNumber = (index + dashboardState.currentStartLine);
        if (lineNumber >= start && lineNumber <= end) {
            row.classList.add('highlighted-line');
        }
    });
}

export function clearHighlightedLines() {
    document.querySelectorAll('.hljs-ln tr.highlighted-line')
        .forEach(row => row.classList.remove('highlighted-line'));
}

export function scrollToLine(lineNumber) {
    const index = lineNumber - dashboardState.currentStartLine;
    const rows = document.querySelectorAll('.hljs-ln tr');
    const row = rows[index];
    if (row) {
        row.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
} 