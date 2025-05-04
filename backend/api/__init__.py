from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import json
import os
import torch
# hf import
from transformers import AutoTokenizer, AutoModelForSequenceClassification

# Constants
ICD_MODEL_NAME = "AkshatSurolia/ICD-10-Code-Prediction"
ICD_CACHE_DIR  = os.path.join(os.path.dirname(__file__), "models", "icd10")


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
        os.makedirs(ICD_CACHE_DIR, exist_ok=True)

        # Load the tokenizer and model for ICD-10 code prediction
        icd_tokenizer = AutoTokenizer.from_pretrained(ICD_MODEL_NAME, cache_dir=ICD_CACHE_DIR)
        icd_model = AutoModelForSequenceClassification.from_pretrained(ICD_MODEL_NAME, cache_dir=ICD_CACHE_DIR)
        device        = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        icd_model.to(device)

        app.state.icd10["tokenizer"] = icd_tokenizer
        app.state.icd10["model"] = icd_model
        app.state.icd10["device"] = device

    from api.chat import chat_router
    from api.transcribe import transcribe_router
    

    app.include_router(chat_router)
    app.include_router(transcribe_router)

    return app  # Returning `get_config` for dependency injection if needed
