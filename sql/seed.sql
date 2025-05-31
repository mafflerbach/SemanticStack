-- Seed data for business tags and initial setup

-- Insert business domain ontology
INSERT INTO business_tags (name, description) VALUES 
    ('billing', 'Invoice generation, payment processing, financial transactions'),
    ('invoicing', 'Invoice creation, delivery, and management'),
    ('customer-management', 'Customer data, profiles, account management'),
    ('authentication', 'User login, session management, security validation'),
    ('notifications', 'Email, SMS, push notifications, alerts'),
    ('reporting', 'Analytics, dashboards, business intelligence'),
    ('cache', 'Data caching, performance optimization, temporary storage'),
    ('integration', 'External API calls, third-party services, data sync'),
    ('analytics', 'Data analysis, metrics collection, tracking'),
    ('validation', 'Input validation, data verification, business rules'),
    ('database', 'Database operations, queries, transactions'),
    ('session', 'Session management, state handling, user context'),
    ('security', 'Security checks, encryption, access control'),
    ('payment', 'Payment processing, card handling, transactions'),
    ('corporate', 'Corporate accounts, business customers, B2B features'),
    ('address', 'Address management, location data, geocoding'),
    ('configuration', 'System settings, feature flags, environment config'),
    ('logging', 'Application logging, audit trails, debugging'),
    ('error-handling', 'Exception handling, error recovery, fault tolerance'),
    ('utility', 'Helper functions, common utilities, shared code')
ON CONFLICT (name) DO NOTHING;

-- Create a view for easy function analysis
CREATE OR REPLACE VIEW function_analysis AS
SELECT 
    f.id as function_id,
    f.filename,
    f.function_name,
    f.class_name,
    f.visibility,
    f.is_static,
    f.return_type,
    COUNT(c.id) as chunk_count,
    COUNT(CASE WHEN c.summary IS NOT NULL THEN 1 END) as enriched_chunks,
    ARRAY_AGG(DISTINCT bt.name ORDER BY bt.name) FILTER (WHERE bt.name IS NOT NULL) as business_domains,
    COUNT(DISTINCT cv.variable_name) as unique_variables,
    f.start_line,
    f.end_line,
    (f.end_line - f.start_line + 1) as total_lines,
    f.created_at
FROM functions f
LEFT JOIN code_chunks c ON f.id = c.function_id
LEFT JOIN chunk_business_tags cbt ON c.id = cbt.chunk_id
LEFT JOIN business_tags bt ON cbt.tag_id = bt.id
LEFT JOIN chunk_variables cv ON c.id = cv.chunk_id
GROUP BY f.id, f.filename, f.function_name, f.class_name, f.visibility, 
         f.is_static, f.return_type, f.start_line, f.end_line, f.created_at;
