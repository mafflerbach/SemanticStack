#!/opt/homebrew/bin/bash

# Complete Code Analysis Pipeline
# Runs parser -> enricher -> API startup

set -e

echo "🚀 Code Analysis Pipeline"
echo "========================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check prerequisites
print_status "Checking prerequisites..."

if ! command -v docker-compose &> /dev/null; then
    print_error "docker-compose not found. Please install Docker Compose."
    exit 1
fi

if [ ! -f "docker-compose.yml" ]; then
    print_error "docker-compose.yml not found. Please run from project root."
    exit 1
fi

# Wait for database
print_status "Starting database..."
docker-compose up postgres -d

print_status "Waiting for database to be ready..."
timeout=60
counter=0
while ! docker-compose exec postgres pg_isready -U analyzer -d codeanalysis -q 2>/dev/null; do
    if [ $counter -ge $timeout ]; then
        print_error "Database failed to start within $timeout seconds"
        exit 1
    fi
    sleep 2
    counter=$((counter + 2))
    echo -n "."
done
echo
print_success "Database is ready"

# Show database stats before processing
print_status "Current database status:"
docker-compose exec postgres psql -U analyzer -d codeanalysis -t -c "
SELECT 
    'Files: ' || COUNT(*) 
FROM files
UNION ALL
SELECT 
    'Functions: ' || COUNT(*) 
FROM functions
UNION ALL
SELECT 
    'Code Chunks: ' || COUNT(*) 
FROM code_chunks
UNION ALL
SELECT 
    'Enriched Chunks: ' || COUNT(*) 
FROM code_chunks WHERE enriched_at IS NOT NULL;
" | sed 's/^[ \t]*//'

# Ask user what to do
echo
echo "Pipeline options:"
echo "1. Full pipeline (parse + enrich)"
echo "2. Parse only"
echo "3. Enrich only"
echo "4. Skip to API startup"
echo "5. Show statistics only"

read -p "Choose option (1-5) [1]: " choice
choice=${choice:-1}

case $choice in
    1)
        print_status "Running full pipeline..."
        RUN_PARSER=true
        RUN_ENRICHER=true
        START_API=true
        ;;
    2)
        print_status "Running parser only..."
        RUN_PARSER=true
        RUN_ENRICHER=false
        START_API=false
        ;;
    3)
        print_status "Running enricher only..."
        RUN_PARSER=false
        RUN_ENRICHER=true
        START_API=false
        ;;
    4)
        print_status "Starting API only..."
        RUN_PARSER=false
        RUN_ENRICHER=false
        START_API=true
        ;;
    5)
        print_status "Showing statistics..."
        RUN_PARSER=false
        RUN_ENRICHER=false
        START_API=false
        ;;
    *)
        print_error "Invalid option"
        exit 1
        ;;
esac

# Run parser if requested
if [ "$RUN_PARSER" = true ]; then
    print_status "Step 1: Running AST Parser..."
    if docker-compose --profile parser up parser; then
        print_success "Parser completed successfully"
    else
        print_error "Parser failed"
        exit 1
    fi
    
    # Show parsing results
    print_status "Parsing results:"
    docker-compose exec postgres psql -U analyzer -d codeanalysis -t -c "
    SELECT 
        'New files parsed: ' || COUNT(*)
    FROM files 
    WHERE parsed_at > NOW() - INTERVAL '5 minutes'
    UNION ALL
    SELECT 
        'New functions found: ' || COUNT(*)
    FROM functions f
    JOIN files fi ON f.file_id = fi.id
    WHERE fi.parsed_at > NOW() - INTERVAL '5 minutes'
    UNION ALL
    SELECT 
        'New code chunks: ' || COUNT(*)
    FROM code_chunks cc
    JOIN functions f ON cc.function_id = f.id
    JOIN files fi ON f.file_id = fi.id
    WHERE fi.parsed_at > NOW() - INTERVAL '5 minutes';
    " | sed 's/^[ \t]*//'
fi

# Run enricher if requested
if [ "$RUN_ENRICHER" = true ]; then
    print_status "Step 2: Running LLM Enricher..."
    
    # Check if there are chunks to enrich
    pending_chunks=$(docker-compose exec postgres psql -U analyzer -d codeanalysis -t -c "
    SELECT COUNT(*) FROM code_chunks WHERE enriched_at IS NULL;
    " | tr -d ' ')
    
    if [ "$pending_chunks" -eq 0 ]; then
        print_warning "No chunks need enrichment. All chunks are already processed."
    else
        print_status "Found $pending_chunks chunks to enrich..."
        
        if docker-compose --profile enrichment up enricher; then
            print_success "Enrichment completed successfully"
        else
            print_error "Enrichment failed"
            exit 1
        fi
    fi
    
    # Show enrichment results
    print_status "Enrichment results:"
    docker-compose exec postgres psql -U analyzer -d codeanalysis -t -c "
    SELECT 
        'Total enriched: ' || COUNT(*) || ' chunks'
    FROM code_chunks 
    WHERE enriched_at IS NOT NULL
    UNION ALL
    SELECT 
        'Average complexity: ' || ROUND(AVG(complexity_score), 2)
    FROM code_chunks 
    WHERE complexity_score IS NOT NULL
    UNION ALL
    SELECT 
        'Average business impact: ' || ROUND(AVG(business_impact_score), 2)
    FROM code_chunks 
    WHERE business_impact_score IS NOT NULL;
    " | sed 's/^[ \t]*//'
fi

# Start API if requested
if [ "$START_API" = true ]; then
    print_status "Step 3: Starting API server..."
    docker-compose up api -d
    
    # Wait for API to be ready
    print_status "Waiting for API to be ready..."
    timeout=30
    counter=0
    while ! curl -s http://localhost:8000/health > /dev/null 2>&1; do
        if [ $counter -ge $timeout ]; then
            print_warning "API health check timeout, but continuing..."
            break
        fi
        sleep 2
        counter=$((counter + 2))
        echo -n "."
    done
    echo
    print_success "API is running at http://localhost:8000"
fi

# Always show final statistics
print_status "Final Statistics:"
echo "=================="
docker-compose exec postgres psql -U analyzer -d codeanalysis -c "
SELECT 
    'Files' as entity,
    COUNT(*) as total,
    COUNT(CASE WHEN parsed_at > NOW() - INTERVAL '1 hour' THEN 1 END) as recent
FROM files
UNION ALL
SELECT 
    'Functions' as entity,
    COUNT(*) as total,
    0 as recent
FROM functions
UNION ALL
SELECT 
    'Code Chunks' as entity,
    COUNT(*) as total,
    COUNT(CASE WHEN enriched_at IS NOT NULL THEN 1 END) as enriched
FROM code_chunks;
"

# Show running services
print_status "Running services:"
docker-compose ps

echo
print_success "Pipeline completed! 🎉"

if [ "$START_API" = true ]; then
    echo
    echo "🌐 API Endpoints:"
    echo "  Health Check: http://localhost:8000/health"
    echo "  Documentation: http://localhost:8000/docs"
    echo "  Database Admin: http://localhost:8080 (if pgAdmin profile enabled)"
fi
