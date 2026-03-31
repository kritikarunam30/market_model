import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.risk import router as risk_router
from app.routes.analysis import router as analysis_router
from app.routes.forecast import router as forecast_router
from app.routes.network import router as network_router

app = FastAPI(title="Global Market Contagion & Systemic Risk Intelligence System")

default_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
env_origins = os.getenv("CORS_ALLOW_ORIGINS", "")
allowed_origins = [origin.strip() for origin in env_origins.split(",") if origin.strip()] or default_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "API is running"}

app.include_router(risk_router, prefix="/api")
app.include_router(analysis_router, prefix="/api")
app.include_router(forecast_router, prefix="/api")
app.include_router(network_router, prefix="/api")

@app.get("/api/health")
def health():
    return {"status": "ok"}