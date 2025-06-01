// Utility Helper Functions
import { CONFIG } from '../config/constants.js';

export function parseParameters(parameters) {
    try {
        const parsedParams = JSON.parse(parameters);
        return Array.isArray(parsedParams) ? parsedParams : [];
    } catch (e) {
        console.warn('Parameter parsing failed:', e);
        return [];
    }
}

export function formatParameters(params) {
    if (!Array.isArray(params)) return '—';
    return params
        .map(p => `${p.name}${p.default !== undefined ? ` = ${p.default}` : ''}`)
        .join(', ');
}

export function calculateProgress(progress) {
    const percentage = progress.total_chunks > 0 
        ? (progress.enriched_chunks / progress.total_chunks * 100).toFixed(1)
        : 0;
    
    const eta = progress.pending_chunks > 0 
        ? Math.ceil(progress.pending_chunks / CONFIG.CHUNKS_PER_MINUTE)
        : 0;

    return { percentage, eta };
}

export function groupByFilepath(items) {
    return items.reduce((acc, item) => {
        if (!acc[item.filepath]) {
            acc[item.filepath] = [];
        }
        acc[item.filepath].push(item);
        return acc;
    }, {});
}

export function filterHighComplexLowImpact(functions) {
    const enriched = functions.filter(f => f.avg_complexity > 0 && f.avg_impact > 0);
    return enriched.filter(f => 
        f.avg_complexity > CONFIG.HIGH_COMPLEXITY_THRESHOLD && 
        f.avg_impact < CONFIG.LOW_IMPACT_THRESHOLD
    );
}

export function getTopComplexFunctions(functions, limit = CONFIG.MAX_COMPLEX_FUNCTIONS_DISPLAY) {
    return functions
        .filter(f => f.avg_complexity > 0)
        .sort((a, b) => b.avg_complexity - a.avg_complexity)
        .slice(0, limit);
}

export function isStacktraceInput(input) {
    return input.includes('::');
}

export function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
} 