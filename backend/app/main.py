import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database.connection import test_connection
from app.api.routes.jobs import router as jobs_router
from app.api.routes.prediction import router as prediction_router
from app.api.routes.scrape import router as scrape_router

cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

app = FastAPI(
    title="Fake Job Posting Detector API",
    description="ML-powered API for detecting potentially fraudulent job postings.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

test_connection()

app.include_router(
    jobs_router,
    prefix="/api"
)
app.include_router(
    prediction_router,
    prefix="/api/v1"
)
app.include_router(
    scrape_router,
    prefix="/api/v1"
)
@app.get("/")

def root():
    return {
        "message" : "Fake Job Detector is running..."
    }
    
@app.get("/api/health")

def health_check():
    return {
        "status" : "ok",
        "message" : "Backend is running..."
    }