from fastapi import FastAPI, HTTPException, Query, Body, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Tuple
import os

# Import routers
from app.routes.health import router as health_router
from app.routes.stats import router as stats_router
from app.routes.functions import get_db, get_async_db, DATABASE_URL
from app.routes.search import router as search_router
from app.routes.code import router as code_router
from app.routes.chunks import router as chunks_router
from app.routes.summaries import router as summaries_router
from app.routes.assessments import router as assessments_router



# from app.routes.stacktrace import router as stacktrace_router

from app.routes.models import SearchResult, ProgressStats, StacktraceRequest

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
    code_router,
    summaries_router,
    chunks_router,
    search_router,
    assessments_router,
]

for router in routers_to_include:
    print("Mounting router with routes:", [route.path for route in router.routes])
    app.include_router(router, prefix="")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Code Analysis API v2", "status": "running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
