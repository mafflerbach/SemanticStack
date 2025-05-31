#!/opt/homebrew/bin/bash

# Status check script for code analysis project

echo "📊 Code Analysis Project Status"
echo "==============================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Check if Docker Compose is running
echo -e "\n${BLUE}🐳 Docker Services:${NC}"
if docker-compose ps | grep -q "Up"; then
    docker-compose ps
else
    echo -e "${RED}No services running${NC}"
fi

# Check database connection
echo -e "\n${BLUE}💾 Database Status:${NC}"
if docker-compose exec postgres pg_isready -U analyzer -d codeanalysis -q 2>/dev/null; then
    echo -e "${GREEN}✅ Database is ready${NC}"
    
    # Database statistics
    echo -e "\n${BLUE}📈 Database Statistics:${NC}"
    docker-compose exec postgres psql -U analyzer -d codeanalysis -c "
    SELECT 
        'Files' as entity,
        COUNT(*) as count,
        COALESCE(MAX(parsed_at)::text, 'Never') as last_updated
    FROM files
    UNION ALL
    SELECT 
        'Functions' as entity,
        COUNT(*) as count,
        COALESCE(MAX(created_at)::text, 'Never') as last_updated
    FROM functions
    UNION ALL
    SELECT 
        'Code Chunks' as entity,
        COUNT(*) as count,
        COALESCE(MAX(created_at)::text, 'Never') as last_updated
    FROM code_chunks
    UNION ALL
    SELECT 
        'Enriched Chunks' as entity,
        COUNT(*) as count,
        COALESCE(MAX(enriched_at)::text, 'Never') as last_updated
    FROM code_chunks 
    WHERE enriched_at IS NOT NULL;
    "
    
    # Enrichment progress
    echo -e "\n${BLUE}🧠 Enrichment Progress:${NC}"
    docker-compose exec postgres psql -U analyzer -d codeanalysis -c "
    WITH progress AS (
        SELECT 
            COUNT(*) as total_chunks,
            COUNT(enriched_at) as enriched_chunks,
            COUNT(*) - COUNT(enriched_at) as pending_chunks
        FROM code_chunks
    )
    SELECT 
        total_chunks,
        enriched_chunks,
        pending_chunks,
        CASE 
            WHEN total_chunks > 0 
            THEN ROUND((enriched_chunks * 100.0 / total_chunks)::numeric, 1) || '%'
            ELSE '0%'
        END as completion_percentage
    FROM progress;
    "
    
    # Recent activity
    echo -e "\n${BLUE}⏰ Recent Activity:${NC}"
    docker-compose exec postgres psql -U analyzer -d codeanalysis -c "
    SELECT 
        'Files parsed in last hour' as activity,
        COUNT(*) as count
    FROM files 
    WHERE parsed_at > NOW() - INTERVAL '1 hour'
    UNION ALL
    SELECT 
        'Chunks enriched in last hour' as activity,
        COUNT(*) as count
    FROM code_chunks 
    WHERE enriched_at > NOW() - INTERVAL '1 hour'
    UNION ALL
    SELECT 
        'Functions with high complexity' as activity,
        COUNT(*) as count
    FROM functions 
    WHERE cyclomatic_complexity > 10;
    "
    
else
    echo -e "${RED}❌ Database not accessible${NC}"
fi

# Check API status
echo -e "\n${BLUE}🌐 API Status:${NC}"
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ API is running at http://localhost:8000${NC}"
    echo "   Documentation: http://localhost:8000/docs"
else
    echo -e "${RED}❌ API not accessible at http://localhost:8000${NC}"
fi

# Check LLM endpoint
echo -e "\n${BLUE}🤖 LLM Endpoint Status:${NC}"
LLM_ENDPOINT=${LLM_ENDPOINT:-"http://host.docker.internal:1234"}
if curl -s "${LLM_ENDPOINT}/health" > /dev/null 2>&1 || curl -s "${LLM_ENDPOINT}" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ LLM endpoint accessible${NC}"
else
    echo -e "${YELLOW}⚠️  LLM endpoint not accessible at ${LLM_ENDPOINT}${NC}"
    echo "   Make sure your LLM server is running"
fi

# Check disk usage for models
echo -e "\n${BLUE}💿 Model Storage:${NC}"
if [ -d "./models" ]; then
    MODEL_SIZE=$(du -sh ./models 2>/dev/null | cut -f1)
    echo "   Models directory: ${MODEL_SIZE:-"0B"}"
else
    echo "   Models directory: Not found"
fi

# Show available commands
echo -e "\n${BLUE}🛠️  Available Commands:${NC}"
echo "   ./scripts/full-pipeline.sh  - Run complete pipeline"
echo "   ./scripts/status.sh         - Show this status"
echo "   docker-compose --profile parser up parser      - Parse code only"
echo "   docker-compose --profile enrichment up enricher - Enrich only"
echo "   docker-compose up api -d    - Start API"
echo "   docker-compose down         - Stop all services"

echo -e "\n${GREEN}Status check complete!${NC}"
