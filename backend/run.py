"""
Convenience Runner Script for FastAPI Backend
Run with: python run.py (inside backend folder or using backend/venv)
"""
import sys
import uvicorn
from app.core.config import settings

if __name__ == "__main__":
    print(f"Starting Pedestrian Routing Backend on http://{settings.HOST}:{settings.PORT}")
    print(f"Swagger Documentation available at: http://{settings.HOST}:{settings.PORT}/docs")
    print(f"Health Check endpoint: http://{settings.HOST}:{settings.PORT}/api/health")
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
