#!/opt/homebrew/bin/bash

# Ultra-compact status for watch command
# Usage: watch -n 1 ./scripts/watch-compact.sh

printf "Code Analysis Status - %s\n" "$(date '+%H:%M:%S')"
printf "=====================================\n"

# Single query for all stats
if docker-compose exec postgres pg_isready -U analyzer -d codeanalysis -q 2>/dev/null; then
    docker-compose exec postgres psql -U analyzer -d codeanalysis -t -A -c "
    WITH stats AS (
        SELECT 
            COUNT(*) as total,
            COUNT(enriched_at) as done,
            COUNT(*) - COUNT(enriched_at) as pending,
            COUNT(CASE WHEN enriched_at > NOW() - INTERVAL '1 minute' THEN 1 END) as rate_1m,
            COUNT(CASE WHEN enriched_at > NOW() - INTERVAL '5 minutes' THEN 1 END) as rate_5m
        FROM code_chunks
    )
    SELECT 
        printf('Chunks: %d/%d (%d%%) | Pending: %d', 
               done, total, 
               CASE WHEN total > 0 THEN (done * 100 / total) ELSE 0 END,
               pending),
        printf('Rate: %d/min | %d/5min', rate_1m, rate_5m),
        CASE 
            WHEN pending = 0 THEN 'Status: ✅ COMPLETE'
            WHEN rate_1m > 0 THEN printf('ETA: ~%d min', pending / rate_1m)
            ELSE 'Status: ⏸️ Paused'
        END
    FROM stats;
    " 2>/dev/null | sed 's/|/\n/g'
else
    echo "❌ Database not accessible"
    exit 1
fi

# Service status (one line)
printf "\nServices: "
POSTGRES=$(docker-compose ps postgres 2>/dev/null | grep -q "Up" && echo "DB:✅" || echo "DB:❌")
API=$(docker-compose ps api 2>/dev/null | grep -q "Up" && echo "API:✅" || echo "API:❌") 
ENRICHER=$(docker-compose ps enricher 2>/dev/null | grep -q "Up" && echo "ENR:✅" || echo "ENR:❌")
LM_STUDIO=$(curl -s http://localhost:1234/ > /dev/null 2>&1 && echo "LLM:✅" || echo "LLM:❌")

printf "%s %s %s %s\n" "$POSTGRES" "$API" "$ENRICHER" "$LM_STUDIO"

# Latest enriched chunk info
printf "\nLatest: "
docker-compose exec postgres psql -U analyzer -d codeanalysis -t -A -c "
SELECT 
    f.function_name || ' (complexity: ' || 
    COALESCE(cc.complexity_score::text, 'N/A') || ')'
FROM code_chunks cc
JOIN functions f ON cc.function_id = f.id  
WHERE cc.enriched_at IS NOT NULL
ORDER BY cc.enriched_at DESC 
LIMIT 1;
" 2>/dev/null || echo "None yet"
