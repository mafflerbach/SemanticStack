from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Tuple
from .functions import get_db, get_async_db

from .models import SearchResult, ProgressStats

router = APIRouter(prefix="", tags=["stats"])


# Stats endpoints
@router.get("/stats")
def get_stats():
    """Get enhanced database statistics"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM files")
    file_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM functions")
    function_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM code_chunks")
    chunk_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM business_tags")
    tag_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT AVG(cyclomatic_complexity) FROM functions WHERE cyclomatic_complexity > 0")
    avg_complexity = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT MAX(nesting_level) FROM code_chunks")
    max_nesting = cursor.fetchone()[0] or 0
    
    cursor.close()
    conn.close()
    
    return {
        "files": file_count,
        "functions": function_count,
        "chunks": chunk_count,
        "business_tags": tag_count,
        "avg_complexity": round(float(avg_complexity), 2),
        "max_nesting_level": max_nesting,
        "database": "postgresql-enhanced"
    }

@router.get("/stats/progress", response_model=ProgressStats)
async def get_progress():
    """Get overall enrichment progress"""
    conn = await get_async_db()
    try:
        query = """
        SELECT 
            COUNT(*) as total_chunks,
            COUNT(enriched_at) as enriched_chunks,
            COUNT(*) - COUNT(enriched_at) as pending_chunks,
            ROUND(AVG(complexity_score)::numeric, 2) as avg_complexity,
            ROUND(AVG(business_impact_score)::numeric, 2) as avg_impact
        FROM code_chunks
        """
        row = await conn.fetchrow(query)
        return ProgressStats(**dict(row))
    finally:
        await conn.close()


@router.get("/stats/summary")
async def get_summary_stats():
    """Get summary statistics for the dashboard"""
    conn = await get_async_db()
    try:
        query = """
        SELECT 
            (SELECT COUNT(*) FROM files) as total_files,
            (SELECT COUNT(*) FROM functions) as total_functions,
            (SELECT COUNT(*) FROM code_chunks) as total_chunks,
            (SELECT COUNT(*) FROM code_chunks WHERE enriched_at IS NOT NULL) as enriched_chunks,
            (SELECT COUNT(*) FROM code_chunks WHERE enriched_at > NOW() - INTERVAL '1 hour') as recent_enriched,
            (SELECT ROUND(AVG(complexity_score)::numeric, 3) FROM code_chunks WHERE complexity_score IS NOT NULL) as avg_complexity,
            (SELECT ROUND(AVG(business_impact_score)::numeric, 3) FROM code_chunks WHERE business_impact_score IS NOT NULL) as avg_impact,
            (SELECT COUNT(*) FROM functions WHERE id IN (
                SELECT function_id FROM code_chunks 
                WHERE complexity_score > 0.7 
                GROUP BY function_id
            )) as high_complexity_functions
        """
        
        row = await conn.fetchrow(query)
        return dict(row)
    finally:
        await conn.close()
