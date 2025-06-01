// Code Viewer Component
import { parseParameters, formatParameters } from '../../utils/helpers.js';
import store from '../../state/store.js';

export class CodeViewer {
    constructor(metaContainer, codeContainer) {
        this.metaContainer = metaContainer;
        this.codeContainer = codeContainer;
        this.highlightedLines = new Set();
    }

    async displayFunction(functionData) {
        const { code, start_line, end_line, function_name, parameters } = functionData;
        
        const parsedParams = parseParameters(parameters);
        const paramStr = formatParameters(parsedParams);
        
        // Store current start line in state
        store.setCurrentFunction(functionData, start_line);

        // Render metadata
        this.renderMetadata(function_name, paramStr, start_line, end_line);
        
        // Render code
        this.renderCode(function_name, paramStr, code, start_line);
    }

    renderMetadata(functionName, paramStr, startLine, endLine) {
        if (this.metaContainer) {
            this.metaContainer.innerHTML = `
                <strong>${functionName}(${paramStr})</strong><br>
                <sl-badge variant="neutral">Lines: ${startLine}–${endLine}</sl-badge>
            `;
        }
    }

    renderCode(functionName, paramStr, code, startLine) {
        const functionHeader = `${functionName}(${paramStr}) `;
        const codeElement = this.codeContainer.querySelector('pre code');
        
        codeElement.textContent = functionHeader + (code || '// No source code found');

        // Reset highlighting
        delete codeElement.dataset.highlighted;
        codeElement.className = 'php';
        hljs.highlightElement(codeElement);

        // Add line numbers
        hljs.lineNumbersBlock(codeElement, {
            startFrom: startLine || 0
        });
    }

    highlightLines(start, end) {
        this.clearHighlights();
        
        const { currentStartLine } = store.getState();
        
        document.querySelectorAll('.hljs-ln tr').forEach((row, index) => {
            const lineNumber = index + currentStartLine;
            if (lineNumber >= start && lineNumber <= end) {
                row.classList.add('highlighted-line');
                this.highlightedLines.add(row);
            }
        });

        this.scrollToLine(start);
    }

    clearHighlights() {
        this.highlightedLines.forEach(row => {
            row.classList.remove('highlighted-line');
        });
        this.highlightedLines.clear();
    }

    scrollToLine(lineNumber) {
        const { currentStartLine } = store.getState();
        const index = lineNumber - currentStartLine;
        const rows = document.querySelectorAll('.hljs-ln tr');
        const row = rows[index];
        
        if (row) {
            row.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }
} 