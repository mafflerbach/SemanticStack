from fastapi import APIRouter
from app.routes.functions import get_db, get_async_db, DATABASE_URL

router = APIRouter(prefix="", tags=["code"])

@router.get("/code/{function_id}")
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
