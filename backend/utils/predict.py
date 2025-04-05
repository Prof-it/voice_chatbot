import joblib
import logging
from .preprocess import preprocess_text

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

model = joblib.load("models/ent_symptom_model.pkl")
vectorizer = joblib.load("models/vectorizer.pkl")
label_encoder = joblib.load("models/label_encoder.pkl")

def predict_diseases1(symptom_texts):
    """
    Accepts either a single symptom string or a list of symptom strings.
    Returns the predicted disease(s).
    """
    # Check if the input is a list of symptoms
    logger.info(f"Received input: {symptom_texts} of type {type(symptom_texts)}")
    
    # If a single string is passed, convert it into a list
    if isinstance(symptom_texts, str):
        symptom_texts = [symptom_texts]


    cleaned_texts = [preprocess_text(text) for text in symptom_texts]    

    # Log the cleaned texts
    logger.info(f"Cleaned texts: {cleaned_texts}")

    # Transform the list of symptom strings using the vectorizer
    text_vectorized = vectorizer.transform(cleaned_texts)
    # Get predictions for each text entry
    predictions = model.predict(text_vectorized)
    # Convert numerical labels back to disease names
    predicted_diseases = label_encoder.inverse_transform(predictions)
    return predicted_diseases

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