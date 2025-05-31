#!/opt/homebrew/bin/bash

# Code Analysis Enrichment Runner
# This script runs the various stages of the code analysis pipeline

set -e

echo "🚀 Code Analysis Pipeline"
echo "========================"

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose not found. Please install Docker Compose."
    exit 1
fi

# Function to wait for database
wait_for_db() {
    echo "⏳ Waiting for database to be ready..."
    while ! docker-compose exec postgres pg_isready -U analyzer -d codeanalysis -q; do
        sleep 2
    done
    echo "✅ Database is ready"
}

# Function to run the parser
run_parser() {
    echo "🔍 Running AST Parser..."
    docker-compose --profile parser up parser
    echo "✅ Parsing completed"
}

# Function to run the enricher
run_enricher() {
    echo "🧠 Running LLM Enricher..."
    docker-compose --profile enrichment up enricher
    echo "✅ Enrichment completed"
}

# Function to show statistics
show_stats() {
    echo "📊 Database Statistics:"
    echo "======================"
    
    docker-compose exec postgres psql -U analyzer -d codeanalysis -c "
    SELECT 
        'Files' as entity,
        COUNT(*) as total
    FROM files
    UNION ALL
    SELECT 
        'Functions' as entity,
        COUNT(*) as total
    FROM functions
    UNION ALL
    SELECT 
        'Code Chunks' as entity,
        COUNT(*) as total
    FROM code_chunks
    UNION ALL
    SELECT 
        'Enriched Chunks' as entity,
        COUNT(*) as total
    FROM code_chunks 
    WHERE enriched_at IS NOT NULL;
    "
    
    echo ""
    echo "📈 Enrichment Progress:"
    docker-compose exec postgres psql -U analyzer -d codeanalysis -c "
    SELECT 
        ROUND(COUNT(CASE WHEN enriched_at IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 1) as enrichment_percentage,
        COUNT(CASE WHEN enriched_at IS NOT NULL THEN 1 END) as enriched,
        COUNT(*) - COUNT(CASE WHEN enriched_at IS NOT NULL THEN 1 END) as pending,
        COUNT(*) as total
    FROM code_chunks;
    "
}

# Main menu
case "${1:-menu}" in
    "parse")
        wait_for_db
        run_parser
        ;;
    "enrich")
        wait_for_db
        run_enricher
        ;;
    "full")
        wait_for_db
        run_parser
        run_enricher
        show_stats
        ;;
    "stats")
        wait_for_db
        show_stats
        ;;
    "reset")
        echo "🗑️  Resetting enrich
