"""Main FastAPI application for the derivatives trading dashboard."""

import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from api.routes import router

# Load environment variables
load_dotenv()

# Create FastAPI app
app = FastAPI(
    title="Derivatives Trading Dashboard API",
    description="Backend API for the derivatives trading dashboard",
    version="1.0.0"
)

# Add CORS middleware - allow localhost dev servers and configured origins
allowed_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "Derivatives Trading Dashboard API is running"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)