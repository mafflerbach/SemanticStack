from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Tuple
from .functions import get_db, get_async_db
from .models import SearchResult, ProgressStats
from fastapi import FastAPI, HTTPException, Query, Body, APIRouter
from app.routes.models import SearchResult, ProgressStats, StacktraceRequest

router = APIRouter(prefix="", tags=["search"])

# Search endpoints
@router.get("/search", response_model=List[SearchResult])
async def search_code(
    q: str = Query(..., min_length=2),
    limit: int = Query(20, le=100),
    fuzzy: bool = False
):
    """Search code summaries"""
    conn = await get_async_db()
    try:
        if fuzzy:
            query = """
            SELECT 
                cc.id,
                cc.summary,
                cc.complexity_score,
                cc.business_impact_score,
                cc.start_line,
                cc.end_line,
                f.function_name,
                f.id as function_id,
                f.class_name,
                files.filepath
            FROM code_chunks cc
            JOIN functions f ON cc.function_id = f.id
            JOIN files ON f.file_id = files.id
            WHERE cc.summary ILIKE $1 
            AND cc.enriched_at IS NOT NULL
            AND cc.summary IS NOT NULL
            AND cc.chunk_type = 'block'
            ORDER BY cc.business_impact_score DESC NULLS LAST
            LIMIT $2
            """
            rows = await conn.fetch(query, f'%{q}%', limit)
        else:
            query = """
            SELECT 
                cc.id,
                cc.summary,
                cc.complexity_score,
                cc.business_impact_score,
                cc.start_line,
                cc.end_line,
                f.function_name,
                f.id as function_id,
                f.class_name,
                files.filepath
            FROM code_chunks cc
            JOIN functions f ON cc.function_id = f.id
            JOIN files ON f.file_id = files.id
            WHERE f.function_name = $1
            AND cc.enriched_at IS NOT NULL
            AND cc.summary IS NOT NULL
            AND cc.chunk_type != 'block'
            ORDER BY cc.start_line ASC NULLS LAST
            LIMIT $2
            """
            rows = await conn.fetch(query, q, limit)

        return [SearchResult(**dict(row)) for row in rows]
    finally:
        await conn.close()



# Function endpoints
@router.get("/functions")
def list_functions(limit: int = 20, sort_by: str = "complexity"):
    """List functions with enhanced metrics"""
    conn = get_db()
    cursor = conn.cursor()
    
    sort_column = {
        "complexity": "f.cyclomatic_complexity DESC",
        "lines": "f.lines_of_code DESC", 
        "chunks": "chunk_count DESC",
        "name": "f.function_name ASC"
    }.get(sort_by, "f.cyclomatic_complexity DESC")
    
    cursor.execute(f"""
        SELECT 
            f.function_name,
            fl.filepath,
            f.visibility,
            f.is_static,
            f.cyclomatic_complexity,
            f.parameter_count,
            f.lines_of_code,
            COUNT(c.id) as chunk_count,
            ARRAY_AGG(DISTINCT c.chunk_type) FILTER (WHERE c.chunk_type IS NOT NULL) as chunk_types,
            MAX(c.nesting_level) as max_nesting
        FROM functions f 
        JOIN files fl ON f.file_id = fl.id
        LEFT JOIN code_chunks c ON f.id = c.function_id 
        GROUP BY f.id, f.function_name, fl.filepath, f.visibility, f.is_static, 
                 f.cyclomatic_complexity, f.parameter_count, f.lines_of_code
        ORDER BY {sort_column}
        LIMIT %s
    """, (limit,))
    
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return [
        {
            "function_name": row[0],
            "filepath": row[1],
            "visibility": row[2],
            "is_static": row[3],
            "avg_complexity": row[4],  # Map cyclomatic_complexity to avg_complexity
            "parameter_count": row[5],
            "lines_of_code": row[6],
            "chunk_count": row[7],
            "chunk_types": row[8] or [],
            "max_nesting_level": row[9] or 0
        }
        for row in results
    ]




@router.post("/analyze", response_model=List[SearchResult])
async def analyze_stacktrace(req: StacktraceRequest = Body(...)):
    """Analyze stacktrace & return uniform SearchResult-style output."""
    lines = req.stacktrace.strip().splitlines()
    results: List[SearchResult] = []

    raw_conn = get_db()
    async_conn = await get_async_db()
    cursor = raw_conn.cursor()

    try:
        extracted_names = []

        for line in lines:
            if "::" not in line:
                results.append(SearchResult(
                    id=-1,
                    summary=f"❌ Invalid format: {line}",
                    filepath=None,
                    function_name=None,
                    function_id=None,
                    class_name=None,
                    start_line=None,
                    end_line=None,
                    complexity_score=None,
                    business_impact_score=None,
                    type="error"
                ))
                continue

            filepath, function = line.split("::", 1)
            extracted_names.append(function)

            cursor.execute("""
                SELECT 
                    f.function_name,
                    f.id,
                    f.visibility,
                    f.is_static,
                    f.cyclomatic_complexity,
                    f.parameter_count,
                    f.lines_of_code,
                    COUNT(c.id) as chunk_count,
                    ARRAY_AGG(DISTINCT c.chunk_type) FILTER (WHERE c.chunk_type IS NOT NULL) as chunk_types,
                    MAX(c.nesting_level) as max_nesting
                FROM functions f 
                JOIN files fl ON f.file_id = fl.id
                LEFT JOIN code_chunks c ON f.id = c.function_id 
                WHERE fl.filepath = %s AND f.function_name = %s
                GROUP BY f.id
            """, (filepath, function))

            row = cursor.fetchone()
            if row:
                name, function_id, visibility, is_static, complexity, params, loc, chunks, types, max_nest = row
                static_text = "static " if is_static else ""
                vis_text = f"{visibility} " if visibility else ""
                complexity_text = f"complexity:{complexity}" if complexity is not None else "complexity:?"
                print(row)
                results.append(SearchResult(
                    id=-1,
                    summary=f"✅ {vis_text}{static_text}{name} ({chunks} chunks, {complexity_text}, max nesting:{max_nest or 0})",
                    filepath=filepath,
                    function_name=name,
                    function_id=function_id,
                    class_name=None,
                    start_line=None,
                    end_line=None,
                    complexity_score=complexity,
                    business_impact_score=None,
                    type="function_summary"
                ))
            else:
                results.append(SearchResult(
                    id=-1,
                    summary=f"❌ No function found: {line}",
                    filepath=filepath,
                    function_name=function,
                    function_id=None,
                    class_name=None,
                    start_line=None,
                    end_line=None,
                    complexity_score=None,
                    business_impact_score=None,
                    type="missing"
                ))

        # Fetch enriched related chunks
        if extracted_names:
            placeholders = ','.join(f"${i+1}" for i in range(len(extracted_names)))
            search_query = f"""
            SELECT 
                cc.id,
                cc.summary,
                cc.complexity_score,
                cc.business_impact_score,
                cc.start_line,
                cc.end_line,
                f.function_name,
                f.id as function_id,
                f.class_name,
                files.filepath
            FROM code_chunks cc
            JOIN functions f ON cc.function_id = f.id
            JOIN files ON f.file_id = files.id
            WHERE f.function_name IN ({placeholders})
            AND cc.enriched_at IS NOT NULL
            AND cc.summary IS NOT NULL
            ORDER BY cc.business_impact_score DESC NULLS LAST
            LIMIT 50
            """
            rows = await async_conn.fetch(search_query, *extracted_names)
            for row in rows:
                result = dict(row)
                result["type"] = "chunk"
                results.append(SearchResult(**result))

        return results

    finally:
        cursor.close()
        raw_conn.close()
        await async_conn.close()

