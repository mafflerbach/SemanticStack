-- Enhanced Schema v2 for Production Code Analysis

-- Enable required extensions FIRST
CREATE EXTENSION IF NOT EXISTS vector;

-- Files table (new) - track individual files
CREATE TABLE files (
    id SERIAL PRIMARY KEY,
    filepath VARCHAR(500) UNIQUE NOT NULL,
    file_hash VARCHAR(64) NOT NULL,
    file_size INTEGER,
    lines_of_code INTEGER,
    parsed_at TIMESTAMP DEFAULT NOW(),
    language VARCHAR(20) DEFAULT 'php',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Enhanced functions table
CREATE TABLE functions (
    id SERIAL PRIMARY KEY,
    file_id INTEGER REFERENCES files(id) ON DELETE CASCADE,
    function_name VARCHAR(255) NOT NULL,
    namespace VARCHAR(255),
    class_name VARCHAR(255),
    visibility VARCHAR(20),
    is_static BOOLEAN DEFAULT FALSE,
    is_abstract BOOLEAN DEFAULT FALSE,
    is_final BOOLEAN DEFAULT FALSE,
    return_type VARCHAR(100),
    parameters JSONB,
    start_line INTEGER,
    end_line INTEGER,
    start_byte INTEGER,
    end_byte INTEGER,
    cyclomatic_complexity INTEGER,
    cognitive_complexity INTEGER,
    parameter_count INTEGER,
    lines_of_code INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT unique_function UNIQUE(file_id, function_name)
);

-- Enhanced code chunks table
CREATE TABLE code_chunks (
    id SERIAL PRIMARY KEY,
    function_id INTEGER NOT NULL REFERENCES functions(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    chunk_type VARCHAR(50),
    nesting_level INTEGER DEFAULT 0,
    start_byte INTEGER,
    end_byte INTEGER,
    start_line INTEGER,
    end_line INTEGER,
    code TEXT NOT NULL,
    code_hash VARCHAR(64),
    summary TEXT,
    embedding vector(384),
    complexity_score REAL,
    business_impact_score REAL,
    grouped BOOLEAN DEFAULT FALSE,
    chunk_length_lines INTEGER DEFAULT 0,
    enriched_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT unique_chunk UNIQUE(function_id, chunk_index)
);

-- Business tags
CREATE TABLE business_tags (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    category VARCHAR(50),
    color VARCHAR(7),
    priority INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Chunk business tags
CREATE TABLE chunk_business_tags (
    chunk_id INTEGER REFERENCES code_chunks(id) ON DELETE CASCADE,
    tag_id INTEGER REFERENCES business_tags(id) ON DELETE CASCADE,
    confidence REAL DEFAULT 1.0,
    source VARCHAR(50) DEFAULT 'llm',
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY(chunk_id, tag_id)
);

-- Function dependencies
CREATE TABLE function_dependencies (
    id SERIAL PRIMARY KEY,
    caller_function_id INTEGER REFERENCES functions(id) ON DELETE CASCADE,
    called_function_id INTEGER REFERENCES functions(id) ON DELETE CASCADE,
    call_type VARCHAR(20),
    call_count INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT unique_dependency UNIQUE(caller_function_id, called_function_id)
);

-- Code patterns
CREATE TABLE code_patterns (
    id SERIAL PRIMARY KEY,
    pattern_name VARCHAR(100) NOT NULL,
    pattern_type VARCHAR(50),
    description TEXT,
    severity VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Pattern occurrences
CREATE TABLE pattern_occurrences (
    id SERIAL PRIMARY KEY,
    pattern_id INTEGER REFERENCES code_patterns(id) ON DELETE CASCADE,
    chunk_id INTEGER REFERENCES code_chunks(id) ON DELETE CASCADE,
    confidence REAL DEFAULT 1.0,
    context JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Variables and their usage
CREATE TABLE chunk_variables (
    id SERIAL PRIMARY KEY,
    chunk_id INTEGER REFERENCES code_chunks(id) ON DELETE CASCADE,
    variable_name VARCHAR(100) NOT NULL,
    variable_type VARCHAR(50),
    frequency INTEGER DEFAULT 1,
    first_use_line INTEGER,
    scope VARCHAR(50),
    CONSTRAINT unique_chunk_variable UNIQUE(chunk_id, variable_name)
);

-- Example queries for discovery
CREATE TABLE chunk_example_queries (
    id SERIAL PRIMARY KEY,
    chunk_id INTEGER REFERENCES code_chunks(id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    question_type VARCHAR(50) DEFAULT 'functional',
    category VARCHAR(50),
    embedding vector(384),
    confidence REAL DEFAULT 1.0,
    difficulty_level INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT unique_chunk_question UNIQUE(chunk_id, question)
);

-- Migration analysis
CREATE TABLE migration_assessments (
    id SERIAL PRIMARY KEY,
    function_id INTEGER REFERENCES functions(id) ON DELETE CASCADE,
    migration_priority VARCHAR(20),
    migration_complexity VARCHAR(20),
    migration_effort_hours INTEGER,
    business_impact VARCHAR(20),
    technical_debt_score REAL,
    modernization_strategy TEXT,
    assessed_by VARCHAR(100),
    assessed_at TIMESTAMP DEFAULT NOW()
);

-- Performance tracking
CREATE TABLE processing_status (
    id SERIAL PRIMARY KEY,
    file_id INTEGER REFERENCES files(id) ON DELETE CASCADE,
    stage VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    progress_percentage INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    processing_time_seconds INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT unique_file_stage UNIQUE(file_id, stage)
);

-- Indexes
CREATE INDEX idx_files_hash ON files(file_hash);
CREATE INDEX idx_files_parsed ON files(parsed_at);
CREATE INDEX idx_functions_file ON functions(file_id);
CREATE INDEX idx_functions_class ON functions(class_name);
CREATE INDEX idx_functions_complexity ON functions(cyclomatic_complexity);
CREATE INDEX idx_functions_name ON functions(function_name);
CREATE INDEX idx_chunks_function ON code_chunks(function_id);
CREATE INDEX idx_chunks_type ON code_chunks(chunk_type);
CREATE INDEX idx_chunks_nesting ON code_chunks(nesting_level);
CREATE INDEX idx_chunks_complexity ON code_chunks(complexity_score);
CREATE INDEX idx_chunks_enriched ON code_chunks(enriched_at) WHERE enriched_at IS NOT NULL;
CREATE INDEX idx_chunk_tags_chunk ON chunk_business_tags(chunk_id);
CREATE INDEX idx_chunk_tags_tag ON chunk_business_tags(tag_id);
CREATE INDEX idx_chunk_tags_confidence ON chunk_business_tags(confidence);
CREATE INDEX idx_chunk_vars_chunk ON chunk_variables(chunk_id);
CREATE INDEX idx_chunk_vars_type ON chunk_variables(variable_type);
CREATE INDEX idx_deps_caller ON function_dependencies(caller_function_id);
CREATE INDEX idx_deps_called ON function_dependencies(called_function_id);
CREATE INDEX idx_patterns_chunk ON pattern_occurrences(chunk_id);
CREATE INDEX idx_queries_category ON chunk_example_queries(category);
CREATE INDEX idx_migration_priority ON migration_assessments(migration_priority);
CREATE INDEX idx_status_stage ON processing_status(stage);
