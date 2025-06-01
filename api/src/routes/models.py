from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Tuple


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


class FunctionStats(BaseModel):
    function_name: str
    class_name: Optional[str] = None
    filepath: str
    chunk_count: int
    avg_complexity: Optional[float] = None
    avg_impact: Optional[float] = None
    enriched_chunks: int


class StacktraceRequest(BaseModel):
    stacktrace: str


class ProgressStats(BaseModel):
    total_chunks: int
    enriched_chunks: int
    pending_chunks: int
    avg_complexity: Optional[float] = None
    avg_impact: Optional[float] = None

