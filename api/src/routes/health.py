from fastapi import APIRouter

router = APIRouter(prefix="", tags=["health"])

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "code-analysis-api"}
