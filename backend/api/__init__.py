from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import json
import os
import pandas as pd




def create_app():
    app = FastAPI(title="ENT Symptom Predictor API", version="1.0")

    # Enable CORS (allow frontend requests)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Adjust in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global storage for JSON config
    app.state.icd10 = {}

    @app.on_event("startup")
    async def startup_event():
        """Loads JSON data on FastAPI startup."""
        
        # Ensure the cache directory exists
        # os.makedirs(ICD_CACHE_DIR, exist_ok=True)

    from api.chat import chat_router
    from api.transcribe import transcribe_router
    

    app.include_router(chat_router)
    app.include_router(transcribe_router)

    return app  # Returning `get_config` for dependency injection if needed
