"""
FastAPI Application Entry Point
AI-Driven Multi-Environmental Personalized Pedestrian Routing
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import router as api_router

app = FastAPI(
    title="AI-Driven Multi-Environmental Personalized Pedestrian Routing API",
    description=(
        "Backend API service integrating OpenRouteService, Open-Meteo environmental APIs, "
        "and Overpass greenery data with a multi-criteria pedestrian routing algorithm."
    ),
    version="0.1.0",
    debug=settings.DEBUG,
)

# Enable CORS for React frontend interaction
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes with prefix /api
app.include_router(api_router, prefix="/api")


@app.get("/", summary="Root Index")
async def root():
    """Root endpoint verifying API availability."""
    return {
        "message": "AI-Driven Multi-Environmental Personalized Pedestrian Routing API is running",
        "docs_url": "/docs",
        "health_check": "/api/health",
    }
