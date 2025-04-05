import pytest
import numpy as np
from backend.utils.drug import (
    remove_duplicate_sentences,
    format_drug_info,
    match_drug_relevance,
    search_drug_info,
)

@pytest.fixture
def mock_drug_data():
    return {
        "Paracetamol": {
            "indications_and_usage": "Used for pain and fever. Used for pain and fever.",
            "warnings_and_cautions": ["May cause liver issues.", "Avoid alcohol."],
        },
        "Ibuprofen": {
            "indications_and_usage": "Pain relief. Also helps with inflammation.",
            "adverse_reactions": "Stomach upset and bleeding possible.",
        },
        "Anti-Itch": {
            "indications_and_usage": "Relieves itching. Relieves itching.",
            "warnings_and_cautions": "Use externally only.",
        },
    }

def test_remove_duplicate_sentences():
    text = "This is a sentence. This is a sentence. This is unique!"
    result = remove_duplicate_sentences(text)
    assert result == "This is a sentence. This is unique!"

def test_format_drug_info_deduplicates_and_truncates(mock_drug_data):
    formatted = format_drug_info(mock_drug_data, "Otitis Media")
    assert "Recommended Drugs for Otitis Media" in formatted
    assert "1. **Paracetamol**" in formatted
    assert "2. **Ibuprofen**" in formatted
    assert "3. **Anti-Itch**" not in formatted  # duplicate-normalized to antiitch

def test_match_drug_relevance_ranking(mock_drug_data):
    symptoms = ["pain", "fever", "inflammation"]
    ranked = match_drug_relevance(mock_drug_data, symptoms)
    assert isinstance(ranked, dict)
    assert list(ranked.keys())[0] == "Paracetamol"  # Matches "pain" and "fever"

def test_search_drug_info_returns_clean_output(mock_drug_data):
    predicted = np.array(["Otitis Media"])
    medical_data = {"Otitis Media": mock_drug_data}
    symptoms = ["fever", "pain"]
    result = search_drug_info(predicted, medical_data, symptoms)
    
    assert "Recommended Drugs for Otitis Media" in result
    assert "Paracetamol" in result
    assert "Ibuprofen" in result
