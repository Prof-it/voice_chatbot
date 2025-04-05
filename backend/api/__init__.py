from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import json
import os

def load_json():
    """Loads JSON data from file at startup."""
    # Get the absolute path of the file
    file_path = os.path.join(os.path.dirname(__file__), "ent_drug_data.json")
    
    with open(file_path, "r") as file:
        return json.load(file)

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
    app.state.medical_advice_data = {}

    @app.on_event("startup")
    async def startup_event():
        """Loads JSON data on FastAPI startup."""
        app.state.medical_advice_data = load_json()

    def get_config():
        """Dependency to access config data."""
        return app.state.medical_advice_data

    from api.predict import predict_router
    from api.chat import chat_router

    app.include_router(predict_router)
    app.include_router(chat_router)

    return app, get_config  # Returning `get_config` for dependency injection if needed
