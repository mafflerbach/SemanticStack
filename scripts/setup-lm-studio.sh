#!/opt/homebrew/bin/bash

# Setup script for LM Studio embeddings (384 dimensions)

echo "🔧 Setting up database for LM Studio embeddings (384 dimensions)..."

# Check if database is running
if ! docker-compose exec postgres pg_isready -U analyzer -d codeanalysis -q; then
    echo "❌ Database not accessible. Please start it first:"
    echo "   docker-compose up postgres -d"
    exit 1
fi

echo "📊 Current schema information:"
docker-compose exec postgres psql -U analyzer -d codeanalysis -c "
SELECT 
    column_name, 
    data_type,
    CASE 
        WHEN data_type = 'USER-DEFINED' THEN udt_name 
        ELSE data_type 
    END as actual_type
FROM information_schema.columns 
WHERE table_name = 'code_chunks' AND column_name = 'embedding';"

echo "🔄 Updating embedding column to vector(384) for LM Studio models..."
docker-compose exec postgres psql -U analyzer -d codeanalysis -c "
-- Update code_chunks table to 384 dimensions (for your LM Studio models)
ALTER TABLE code_chunks ALTER COLUMN embedding TYPE vector(384);

-- Update chunk_example_queries table if it exists
DO \$\$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'chunk_example_queries' AND column_name = 'embedding') THEN
        ALTER TABLE chunk_example_queries ALTER COLUMN embedding TYPE vector(384);
        RAISE NOTICE 'Updated chunk_example_queries.embedding to vector(384)';
    END IF;
END\$\$;

-- Drop existing vector indexes (will be recreated after enrichment)
DROP INDEX IF EXISTS idx_chunks_embedding;
DROP INDEX IF EXISTS idx_queries_embedding;"

echo "✅ Migration completed!"

echo "📊 Updated schema:"
docker-compose exec postgres psql -U analyzer -d codeanalysis -c "
SELECT 
    column_name, 
    data_type,
    CASE 
        WHEN data_type = 'USER-DEFINED' THEN udt_name 
        ELSE data_type 
    END as actual_type
FROM information_schema.columns 
WHERE table_name = 'code_chunks' AND column_name = 'embedding';"

echo "🗑️ Clearing any existing embeddings (they may be wrong dimension)..."
docker-compose exec postgres psql -U analyzer -d codeanalysis -c "
UPDATE code_chunks SET 
    embedding = NULL,
    enriched_at = NULL
WHERE embedding IS NOT NULL;

SELECT 'Cleared existing embeddings' as result;"

echo "✅ Database ready for LM Studio embeddings!"
echo ""
echo "📋 Your LM Studio Models:"
echo "  • text-embedding-gguf-multi-qa-minilm-l6-cos-v1 (optimized for Q&A)"
echo "  • text-embedding-all-minilm-l12-v2 (general purpose, larger)"
echo ""
echo "🔧 Configuration:"
echo "  Vector Dimension: 384"
echo "  Default Model: text-embedding-all-minilm-l12-v2"
echo ""
echo "📝 To change the embedding model, update your .env file:"
echo "  EMBEDDING_MODEL_NAME=text-embedding-gguf-multi-qa-minilm-l6-cos-v1"
echo ""
echo "🚀 Next steps:"
echo "  1. Start LM Studio with your embedding model loaded"
echo "  2. Run enrichment: docker-compose --profile enrichment up enricher"
echo "  3. Check progress: ./scripts/status.sh"
