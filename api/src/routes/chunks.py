from fastapi import APIRouter

router = APIRouter(prefix="", tags=["chunks"])

# Chunk analysis endpoints
@router.get("/chunks/analysis")
def chunk_analysis():
    """Analyze chunk types and nesting patterns"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Chunk type distribution
    cursor.execute("""
        SELECT 
            chunk_type, 
            COUNT(*) as count,
            AVG(nesting_level) as avg_nesting,
            MAX(nesting_level) as max_nesting
        FROM code_chunks 
        GROUP BY chunk_type 
        ORDER BY count DESC
    """)
    
    chunk_types = [
        {
            "type": row[0],
            "count": row[1], 
            "avg_nesting": round(float(row[2]), 2),
            "max_nesting": row[3]
        }
        for row in cursor.fetchall()
    ]
    
    # Nesting level distribution
    cursor.execute("""
        SELECT 
            nesting_level,
            COUNT(*) as count,
            ARRAY_AGG(DISTINCT chunk_type) as chunk_types
        FROM code_chunks 
        GROUP BY nesting_level 
        ORDER BY nesting_level
    """)
    
    nesting_levels = [
        {
            "level": row[0],
            "count": row[1],
            "chunk_types": row[2]
        }
        for row in cursor.fetchall()
    ]
    
    cursor.close()
    conn.close()
    
    return {
        "chunk_types": chunk_types,
        "nesting_levels": nesting_levels
    }
