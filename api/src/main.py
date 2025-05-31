from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import asyncpg
import os
import psycopg2
from typing import Dict, List, Optional, Tuple, Any

app = FastAPI(title="Code Analysis API v2", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    return psycopg2.connect(os.getenv("DATABASE_URL"))


@app.get("/stats")
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
    
    return {
        "functions": [
            {
                "name": row[0],
                "filepath": row[1],
                "visibility": row[2],
                "is_static": row[3],
                "cyclomatic_complexity": row[4],
                "parameter_count": row[5],
                "lines_of_code": row[6],
                "chunk_count": row[7],
                "chunk_types": row[8] or [],
                "max_nesting_level": row[9] or 0
            }
            for row in results
        ]
    }

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

class StacktraceRequest(BaseModel):
    stacktrace: str

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




# Add CORS middleware if not already present
app = FastAPI(title="Code Analysis API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # Add your frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database connection
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://analyzer:secure_password_change_me@postgres:5432/codeanalysis')

async def get_db():
    return await asyncpg.connect(DATABASE_URL)

# Data models
class ProgressStats(BaseModel):
    total_chunks: int
    enriched_chunks: int
    pending_chunks: int
    avg_complexity: Optional[float] = None
    avg_impact: Optional[float] = None

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

# API Endpoints
@app.get("/stats/progress", response_model=ProgressStats)
async def get_progress():
    """Get overall enrichment progress"""
    conn = await get_db()
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

@app.get("/functions", response_model=List[FunctionStats])
async def get_functions(
    limit: int = Query(50, le=200),
    include_stats: bool = True,
    order_by: str = Query("complexity", regex="^(complexity|impact|name)$")
):
    """Get function statistics"""
    conn = await get_db()
    try:
        order_clause = {
            "complexity": "avg_complexity DESC NULLS LAST",
            "impact": "avg_impact DESC NULLS LAST", 
            "name": "f.function_name ASC"
        }[order_by]
        
        query = f"""
        SELECT 
            f.function_name,
            f.class_name,
            files.filepath,
            COUNT(cc.id) as chunk_count,
            AVG(cc.complexity_score) as avg_complexity,
            AVG(cc.business_impact_score) as avg_impact,
            COUNT(CASE WHEN cc.enriched_at IS NOT NULL THEN 1 END) as enriched_chunks
        FROM functions f
        JOIN files ON f.file_id = files.id
        LEFT JOIN code_chunks cc ON f.id = cc.function_id
        GROUP BY f.id, f.function_name, f.class_name, files.filepath
        HAVING COUNT(cc.id) > 0
        ORDER BY {order_clause}
        LIMIT {limit}
        """
        
        rows = await conn.fetch(query)
        return [FunctionStats(**dict(row)) for row in rows]
    finally:
        await conn.close()

@app.get("/search", response_model=List[SearchResult])
async def search_code(
    q: str = Query(..., min_length=2),
    limit: int = Query(20, le=100),
    fuzzy: bool = False
):
    """Search code summaries"""
    conn = await get_db()
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
            ORDER BY cc.start_line, end_line ASC NULLS LAST
            LIMIT $2
            """

            rows = await conn.fetch(query, q, limit)

        return [SearchResult(**dict(row)) for row in rows]
    finally:
        await conn.close()


@app.get("/code/{function_id}")
async def get_function_code(function_id: int):
    """Get the full source code and metadata of a function."""
    conn = await get_db()
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

        # We'll assume one 'main' chunk per function
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

def get_sync_db():
    import psycopg2
    return psycopg2.connect(os.getenv("DATABASE_URL"))


from fastapi import APIRouter, Body
from typing import Dict, Any, List

@app.post("/analyze", response_model=List[SearchResult])
async def analyze_stacktrace(req: StacktraceRequest = Body(...)):
    """Analyze stacktrace & return uniform SearchResult-style output."""
    lines = req.stacktrace.strip().splitlines()
    results: List[SearchResult] = []

    raw_conn = get_sync_db()
    async_conn = await get_db()
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
                    function_id=id,
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


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "code-analysis-api"}

@app.get("/stats/summary")
async def get_summary_stats():
    """Get summary statistics for the dashboard"""
    conn = await get_db()
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
