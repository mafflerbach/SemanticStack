from fastapi import FastAPI, HTTPException, Query, Body, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Tuple
import asyncpg
import os
import psycopg2

# Import routers
from app.routes.health import router as health_router
from app.routes.stats import router as stats_router
from app.routes.functions import get_db, get_async_db, DATABASE_URL
# from app.routes.search import router as search_router
# from app.routes.stacktrace import router as stacktrace_router

# Create single FastAPI app instance
app = FastAPI(title="Code Analysis API v2", version="2.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
routers_to_include = [
    health_router,
    stats_router,
    # functions_router,
    # search_router,
    # stacktrace_router,
]

for router in routers_to_include:
    print("Mounting router with routes:", [route.path for route in router.routes])
    app.include_router(router, prefix="")

class FunctionStats(BaseModel):
    function_name: str
    class_name: Optional[str] = None
    filepath: str
    chunk_count: int
    avg_complexity: Optional[float] = None
    avg_impact: Optional[float] = None
    enriched_chunks: int

class SearchResult(BaseModel):
    id: int
    summary: str
    complexity_score: Optional[float] = None
    business_impact_score: Optional[float] = None
    function_name: Optional[str] = None
    function_id: Optional[int] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    type: str
    class_name: Optional[str] = None
    filepath: Optional[str] = None

class StacktraceRequest(BaseModel):
    stacktrace: str

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Code Analysis API v2", "status": "running"}


# Function endpoints
@app.get("/functions")
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

# Search endpoints
@app.get("/search", response_model=List[SearchResult])
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

@app.get("/code/{function_id}")
async def get_function_code(function_id: int):
    """Get the full source code and metadata of a function."""
    conn = await get_async_db()
    try:
        query = """
            SELECT cc.code, f.start_line, f.end_line, f.parameters, f.function_name
            FROM code_chunks cc
            JOIN functions f ON f.id = cc.function_id
            WHERE cc.function_id = $1 AND cc.chunk_type = 'main'
            ORDER BY f.start_line ASC NULLS LAST, cc.chunk_index ASC
        """
        rows = await conn.fetch(query, function_id)

        if not rows:
            raise HTTPException(status_code=404, detail="Function not found or has no 'main' chunk")

        row = rows[0]
        return {
            "code": row["code"],
            "start_line": row["start_line"],
            "function_name": row["function_name"],
            "end_line": row["end_line"],
            "parameters": row["parameters"],
        }
    finally:
        await conn.close()

# Chunk analysis endpoints
@app.get("/chunks/analysis")
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

# Analysis endpoints
@app.post("/summarize") 
def summarize_stacktrace(req: StacktraceRequest):
    """Enhanced stacktrace analysis with complexity metrics"""
    lines = req.stacktrace.strip().splitlines()
    summaries = []
    
    conn = get_db()
    cursor = conn.cursor()
    
    for line in lines:
        if "::" not in line:
            summaries.append(f"❌ Invalid format: {line}")
            continue
            
        filepath, function = line.split("::", 1)
        
        cursor.execute("""
            SELECT 
                f.function_name,
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
            GROUP BY f.id, f.function_name, f.visibility, f.is_static, 
                     f.cyclomatic_complexity, f.parameter_count, f.lines_of_code
        """, (filepath, function))
        
        result = cursor.fetchone()
        if result:
            name, visibility, is_static, complexity, params, lines, chunks, types, max_nest = result
            static_text = "static " if is_static else ""
            vis_text = f"{visibility} " if visibility else ""
            complexity_text = f"complexity:{complexity}" if complexity else "complexity:?"
            
            summary = f"✅ {vis_text}{static_text}{name} ({chunks} chunks, {complexity_text}, max nesting:{max_nest or 0})"
            summaries.append(summary)
        else:
            summaries.append(f"❌ No function found: {line}")
    
    cursor.close()
    conn.close()
    
    return {"summaries": summaries}

@app.post("/analyze", response_model=List[SearchResult])
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

# Migration assessment endpoint
@app.get("/migration/assessment")
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
