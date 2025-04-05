import pytest
from backend.utils.predict import predict_diseases

def test_single_symptom_string():
    input_text = "I have ringing in my ears and dizziness."
    prediction = predict_diseases(input_text)

    assert isinstance(prediction, list)
    assert len(prediction) == 1
    assert isinstance(prediction[0], str)
    print("Prediction:", prediction)

def test_multiple_symptom_inputs():
    input_texts = [
        "My nose is blocked and I have pressure in my head.",
        "I'm experiencing ear pain and some hearing loss."
    ]
    prediction = predict_diseases(input_texts)

    assert isinstance(prediction, list)
    assert len(prediction) == len(input_texts)
    assert all(isinstance(p, str) for p in prediction)
    print("Predictions:", prediction)
