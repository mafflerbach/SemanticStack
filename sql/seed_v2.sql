-- Enhanced seed data for v2 schema

-- Insert enhanced business domain ontology
INSERT INTO business_tags (name, description, category, color, priority) VALUES 
    ('billing', 'Invoice generation, payment processing, financial transactions', 'domain', '#E74C3C', 9),
    ('invoicing', 'Invoice creation, delivery, and management', 'domain', '#9B59B6', 8),
    ('customer-management', 'Customer data, profiles, account management', 'domain', '#3498DB', 8),
    ('authentication', 'User login, session management, security validation', 'domain', '#E67E22', 9),
    ('notifications', 'Email, SMS, push notifications, alerts', 'domain', '#F39C12', 6),
    ('reporting', 'Analytics, dashboards, business intelligence', 'domain', '#27AE60', 7),
    ('cache', 'Data caching, performance optimization, temporary storage', 'pattern', '#95A5A6', 5),
    ('integration', 'External API calls, third-party services, data sync', 'domain', '#34495E', 8),
    ('analytics', 'Data analysis, metrics collection, tracking', 'domain', '#16A085', 7),
    ('validation', 'Input validation, data verification, business rules', 'pattern', '#2ECC71', 8),
    ('database', 'Database operations, queries, transactions', 'pattern', '#8E44AD', 7),
    ('session', 'Session management, state handling, user context', 'pattern', '#F1C40F', 6),
    ('security', 'Security checks, encryption, access control', 'domain', '#C0392B', 9),
    ('payment', 'Payment processing, card handling, transactions', 'domain', '#D35400', 9),
    ('corporate', 'Corporate accounts, business customers, B2B features', 'domain', '#7F8C8D', 8),
    ('address', 'Address management, location data, geocoding', 'domain', '#1ABC9C', 6),
    ('configuration', 'System settings, feature flags, environment config', 'pattern', '#BDC3C7', 5),
    ('logging', 'Application logging, audit trails, debugging', 'pattern', '#ECF0F1', 4),
    ('error-handling', 'Exception handling, error recovery, fault tolerance', 'pattern', '#E74C3C', 7),
    ('utility', 'Helper functions, common utilities, shared code', 'pattern', '#95A5A6', 3)
ON CONFLICT (name) DO NOTHING;

-- Insert common code patterns
INSERT INTO code_patterns (pattern_name, pattern_type, description, severity) VALUES
    ('Long Method', 'anti_pattern', 'Method with too many lines of code', 'warning'),
    ('Complex Conditional', 'anti_pattern', 'Deeply nested or complex if/else statements', 'warning'),
    ('God Function', 'anti_pattern', 'Function doing too many different things', 'error'),
    ('Database Transaction', 'pattern', 'Proper database transaction handling', 'info'),
    ('Error Handling', 'pattern', 'Try-catch blocks and error management', 'info'),
    ('Validation Pattern', 'pattern', 'Input validation and sanitization', 'info'),
    ('Magic Numbers', 'smell', 'Hard-coded numeric values without explanation', 'warning'),
    ('Duplicated Code', 'smell', 'Similar code blocks that could be extracted', 'warning'),
    ('Deep Nesting', 'smell', 'Too many nested control structures', 'warning'),
    ('Large Class', 'smell', 'Class with too many responsibilities', 'warning')
ON CONFLICT (pattern_name) DO NOTHING;

-- Create views for common queries
CREATE OR REPLACE VIEW function_complexity_analysis AS
SELECT 
    f.id as function_id,
    fl.filepath,
    f.function_name,
    f.class_name,
    f.visibility,
    f.is_static,
    f.cyclomatic_complexity,
    f.cognitive_complexity,
    f.lines_of_code,
    f.parameter_count,
    COUNT(c.id) as chunk_count,
    COUNT(CASE WHEN c.summary IS NOT NULL THEN 1 END) as enriched_chunks,
    ARRAY_AGG(DISTINCT bt.name ORDER BY bt.name) FILTER (WHERE bt.name IS NOT NULL) as business_domains,
    COUNT(DISTINCT cv.variable_name) as unique_variables,
    AVG(c.complexity_score) as avg_chunk_complexity,
    MAX(c.business_impact_score) as max_business_impact,
    f.created_at,
    MAX(c.enriched_at) as last_enriched_at
FROM functions f
JOIN files fl ON f.file_id = fl.id
LEFT JOIN code_chunks c ON f.id = c.function_id
LEFT JOIN chunk_business_tags cbt ON c.id = cbt.chunk_id
LEFT JOIN business_tags bt ON cbt.tag_id = bt.id
LEFT JOIN chunk_variables cv ON c.id = cv.chunk_id
GROUP BY f.id, fl.filepath, f.function_name, f.class_name, f.visibility, 
         f.is_static, f.cyclomatic_complexity, f.cognitive_complexity, 
         f.lines_of_code, f.parameter_count, f.created_at;

CREATE OR REPLACE VIEW migration_readiness_report AS
SELECT 
    f.function_name,
    fl.filepath,
    f.cyclomatic_complexity,
    f.lines_of_code,
    COUNT(c.id) as chunk_count,
    COUNT(fd_out.id) as functions_called,
    COUNT(fd_in.id) as called_by_functions,
    COALESCE(ma.migration_priority, 'unassessed') as migration_priority,
    COALESCE(ma.migration_complexity, 'unassessed') as migration_complexity,
    COALESCE(ma.business_impact, 'unassessed') as business_impact,
    ma.technical_debt_score
FROM functions f
JOIN files fl ON f.file_id = fl.id
LEFT JOIN code_chunks c ON f.id = c.function_id
LEFT JOIN function_dependencies fd_out ON f.id = fd_out.caller_function_id
LEFT JOIN function_dependencies fd_in ON f.id = fd_in.called_function_id
LEFT JOIN migration_assessments ma ON f.id = ma.function_id
GROUP BY f.id, fl.filepath, f.function_name, f.cyclomatic_complexity, f.lines_of_code,
         ma.migration_priority, ma.migration_complexity, ma.business_impact, ma.technical_debt_score
ORDER BY f.cyclomatic_complexity DESC, chunk_count DESC;
