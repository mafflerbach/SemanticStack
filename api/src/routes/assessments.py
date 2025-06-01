from fastapi import APIRouter

router = APIRouter(prefix="", tags=["assesments"])


# Migration assessment endpoint
@router.get("/migration/assessment")
def migration_assessment():
    """Generate migration complexity assessment"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            f.function_name,
            f.cyclomatic_complexity,
            f.lines_of_code,
            f.parameter_count,
            COUNT(c.id) as chunk_count,
            MAX(c.nesting_level) as max_nesting,
            CASE 
                WHEN f.cyclomatic_complexity > 10 OR f.lines_of_code > 100 THEN 'high'
                WHEN f.cyclomatic_complexity > 5 OR f.lines_of_code > 50 THEN 'medium'
                ELSE 'low'
            END as migration_risk
        FROM functions f
        LEFT JOIN code_chunks c ON f.id = c.function_id
        GROUP BY f.id, f.function_name, f.cyclomatic_complexity, f.lines_of_code, f.parameter_count
        ORDER BY f.cyclomatic_complexity DESC, f.lines_of_code DESC
    """)

    results = cursor.fetchall()
    cursor.close()
    conn.close()
    
    # Group by risk level
    risk_groups = {"high": [], "medium": [], "low": []}
    
    for row in results:
        risk_level = row[6]
        function_data = {
            "name": row[0],
            "complexity": row[1],
            "lines": row[2], 
            "parameters": row[3],
            "chunks": row[4],
            "max_nesting": row[5]
        }
        risk_groups[risk_level].append(function_data)
    
    return {
        "migration_assessment": risk_groups,
        "summary": {
            "high_risk_count": len(risk_groups["high"]),
            "medium_risk_count": len(risk_groups["medium"]), 
            "low_risk_count": len(risk_groups["low"])
        }
    }
