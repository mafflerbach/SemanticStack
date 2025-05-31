#!/opt/homebrew/bin/bash

# Compact status script optimized for watch command
# Usage: watch -n 2 ./scripts/watch-status.sh

# No colors for watch (can be confusing)
# Get current timestamp
echo "📊 Code Analysis Status - $(date '+%H:%M:%S')"
echo "======================================"

# Check if database is accessible (quiet check)
if ! docker-compose exec postgres pg_isready -U analyzer -d codeanalysis -q 2>/dev/null; then
    echo "❌ Database not accessible"
    exit 1
fi

# Get core statistics in one query
docker-compose exec postgres psql -U analyzer -d codeanalysis -t -A -c "
WITH stats AS (
    SELECT 
        (SELECT COUNT(*) FROM files) as total_files,
        (SELECT COUNT(*) FROM functions) as total_functions,
        (SELECT COUNT(*) FROM code_chunks) as total_chunks,
        (SELECT COUNT(*) FROM code_chunks WHERE enriched_at IS NOT NULL) as enriched_chunks,
        (SELECT COUNT(*) FROM code_chunks WHERE enriched_at > NOW() - INTERVAL '1 minute') as chunks_last_minute,
        (SELECT ROUND(AVG(complexity_score)::numeric, 2) FROM code_chunks WHERE complexity_score IS NOT NULL) as avg_complexity,
        (SELECT ROUND(AVG(business_impact_score)::numeric, 2) FROM code_chunks WHERE business_impact_score IS NOT NULL) as avg_business_impact
)
SELECT 
    'Files: ' || total_files || 
    ' | Functions: ' || total_functions ||
    ' | Chunks: ' || total_chunks as overview,
    'Enriched: ' || enriched_chunks || '/' || total_chunks || 
    ' (' || CASE WHEN total_chunks > 0 THEN ROUND((enriched_chunks * 100.0 / total_chunks)::numeric, 1) ELSE 0 END || '%)' as progress,
    'Remaining: ' || (total_chunks - enriched_chunks) || 
    ' | Last min: ' || chunks_last_minute as remaining,
    'Avg Complexity: ' || COALESCE(avg_complexity::text, 'N/A') || 
    ' | Avg Impact: ' || COALESCE(avg_business_impact::text, 'N/A') as averages
FROM stats;
" 2>/dev/null | while IFS='|' read -r line; do echo "$line"; done

echo ""

# Check running services status
echo "🐳 Services:"
SERVICES_STATUS=$(docker-compose ps --format "table {{.Service}}\t{{.State}}" 2>/dev/null | grep -E "(postgres|api|enricher)" | awk '{printf "%-12s %s\n", $1, $2}')
if [ -n "$SERVICES_STATUS" ]; then
    echo "$SERVICES_STATUS"
else
    echo "No services running"
fi

echo ""

# Check recent activity
echo "⏰ Recent Activity (last 5 minutes):"
docker-compose exec postgres psql -U analyzer -d codeanalysis -t -A -c "
SELECT 
    'Enriched: ' || COUNT(*) || ' chunks'
FROM code_chunks 
WHERE enriched_at > NOW() - INTERVAL '5 minutes'
UNION ALL
SELECT 
    'Files parsed: ' || COUNT(*) || ' files'
FROM files 
WHERE parsed_at > NOW() - INTERVAL '5 minutes';
" 2>/dev/null

# Check LM Studio connection (quick test)
# echo ""
# echo "🤖 LM Studio:"
# if curl -s http://localhost:1234/health > /dev/null 2>&1 || curl -s http://localhost:1234/ > /dev/null 2>&1; then
#     echo "✅ Connected"
# else
#     echo "❌ Not accessible"
# fi

# Show estimated completion time if enrichment is running
PENDING=$(docker-compose exec postgres psql -U analyzer -d codeanalysis -t -A -c "SELECT COUNT(*) FROM code_chunks WHERE enriched_at IS NULL;" 2>/dev/null | tr -d ' ')
RECENT_RATE=$(docker-compose exec postgres psql -U analyzer -d codeanalysis -t -A -c "SELECT COUNT(*) FROM code_chunks WHERE enriched_at > NOW() - INTERVAL '5 minutes';" 2>/dev/null | tr -d ' ')

if [ "$PENDING" -gt 0 ] && [ "$RECENT_RATE" -gt 0 ]; then
    # Calculate ETA (rate per 5 minutes)
    RATE_PER_MIN=$(echo "scale=2; $RECENT_RATE / 5" | bc 2>/dev/null || echo "1")
    ETA_MINUTES=$(echo "scale=0; $PENDING / $RATE_PER_MIN" | bc 2>/dev/null || echo "unknown")
    
    echo ""
    echo "📈 Enrichment Progress:"
    echo "Rate: ~$RATE_PER_MIN chunks/min | ETA: ~${ETA_MINUTES} minutes"
fi
