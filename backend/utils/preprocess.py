import re
from typing import List

def preprocess_text(symptoms: List[str]) -> str:
    """
    Preprocesses a list of symptoms:
    - Lowercases each symptom
    - Removes special characters
    - Strips extra whitespace
    - Deduplicates and joins into a single string
    """
    cleaned = set()

    for symptom in symptoms:
        symptom = symptom.lower()
        symptom = re.sub(r"[^a-zA-Z\s]", "", symptom)
        symptom = symptom.strip()
        if symptom:
            cleaned.add(symptom)

    return ", ".join(sorted(cleaned))
