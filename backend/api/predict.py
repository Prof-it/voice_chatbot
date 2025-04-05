from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import joblib
from utils.preprocess import preprocess_text

predict_router = APIRouter()

# Load pre-trained models
model = joblib.load("models/ent_symptom_model.pkl")
vectorizer = joblib.load("models/vectorizer.pkl")
label_encoder = joblib.load("models/label_encoder.pkl")

class SymptomInput(BaseModel):
    symptoms: str

@predict_router.post("/predict", summary="Predict disease from symptoms")
def predict_disease(data: SymptomInput):
    try:
        symptoms_text = data.symptoms.strip()
        if not symptoms_text:
            raise HTTPException(status_code=400, detail="No symptoms provided")

        # Preprocess input text
        cleaned_text = preprocess_text(symptoms_text)

        # Convert to TF-IDF vector
        text_vectorized = vectorizer.transform([cleaned_text])

        # Predict disease
        prediction = model.predict(text_vectorized)
        predicted_disease = label_encoder.inverse_transform(prediction)[0]

        return {"predicted_disease": predicted_disease}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def predict_diseases(symptom_texts):
    """
    Accepts either a single symptom string or a list of symptom strings.
    Returns the predicted disease(s).
    """
    # If a single string is passed, convert it into a list
    if isinstance(symptom_texts, str):
        symptom_texts = [symptom_texts]
    
    # Transform the list of symptom strings using the vectorizer
    text_vectorized = vectorizer.transform(symptom_texts)
    # Get predictions for each text entry
    predictions = model.predict(text_vectorized)
    # Convert numerical labels back to disease names
    predicted_diseases = label_encoder.inverse_transform(predictions)
    return predicted_diseases