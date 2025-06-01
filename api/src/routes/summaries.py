
from fastapi import APIRouter
from app.routes.models import SearchResult, ProgressStats, StacktraceRequest

router = APIRouter(prefix="", tags=["summaries"])


# Analysis endpoints
@router.post("/summarize") 
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
