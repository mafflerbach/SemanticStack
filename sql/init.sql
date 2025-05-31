-- Database schema initialization

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Functions table (normalized)
CREATE TABLE functions (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(500) NOT NULL,
    function_name VARCHAR(255) NOT NULL,
    namespace VARCHAR(255),
    class_name VARCHAR(255),
    visibility VARCHAR(20),
    is_static BOOLEAN DEFAULT FALSE,
    return_type VARCHAR(100),
    parameters JSONB,
    start_line INTEGER,
    end_line INTEGER,
    start_byte INTEGER,
    end_byte INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT unique_function UNIQUE(filename, function_name)
);

-- Code chunks table (1-to-many with functions)
CREATE TABLE code_chunks (
    id SERIAL PRIMARY KEY,
    function_id INTEGER NOT NULL REFERENCES functions(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    start_byte INTEGER,
    end_byte INTEGER,
    code TEXT NOT NULL,
    summary TEXT,
    embedding vector(768),
    enriched_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT unique_chunk UNIQUE(function_id, chunk_index)
);

-- Business tags lookup table
CREATE TABLE business_tags (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Many-to-many: chunks to business tags
CREATE TABLE chunk_business_tags (
    chunk_id INTEGER REFERENCES code_chunks(id) ON DELETE CASCADE,
    tag_id INTEGER REFERENCES business_tags(id) ON DELETE CASCADE,
    confidence REAL DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT NOW(),
    
    PRIMARY KEY(chunk_id, tag_id)
);

-- Key variables found in chunks
CREATE TABLE chunk_variables (
    id SERIAL PRIMARY KEY,
    chunk_id INTEGER REFERENCES code_chunks(id) ON DELETE CASCADE,
    variable_name VARCHAR(100) NOT NULL,
    frequency INTEGER DEFAULT 1,
    
    CONSTRAINT unique_chunk_variable UNIQUE(chunk_id, variable_name)
);

-- Example questions for discovery
CREATE TABLE chunk_example_queries (
    id SERIAL PRIMARY KEY,
    chunk_id INTEGER REFERENCES code_chunks(id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    question_type VARCHAR(50) DEFAULT 'functional',
    embedding vector(768),
    confidence REAL DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT unique_chunk_question UNIQUE(chunk_id, question)
);

-- Create indexes for performance
CREATE INDEX idx_functions_filename ON functions(filename);
CREATE INDEX idx_functions_class ON functions(class_name) WHERE class_name IS NOT NULL;
CREATE INDEX idx_chunks_function ON code_chunks(function_id);
CREATE INDEX idx_chunks_enriched ON code_chunks(enriched_at) WHERE enriched_at IS NOT NULL;
CREATE INDEX idx_chunk_tags_chunk ON chunk_business_tags(chunk_id);
CREATE INDEX idx_chunk_tags_tag ON chunk_business_tags(tag_id);
CREATE INDEX idx_chunk_vars_chunk ON chunk_variables(chunk_id);
CREATE INDEX idx_chunk_vars_name ON chunk_variables(variable_name);
CREATE INDEX idx_queries_chunk ON chunk_example_queries(chunk_id);
