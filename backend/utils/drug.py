import re
import numpy as np
import logging


logging.basicConfig(level=logging.DEBUG)

def remove_duplicate_sentences(text):
    """ Removes duplicate sentences while keeping the first occurrence. """
    sentences = list(dict.fromkeys(re.split(r'(?<=[.!?])\s+', text)))  # Remove exact duplicates
    return " ".join(sentences)

def format_drug_info(drug_data: dict, disease: str) -> str:
    """
    Formats raw drug info into a clean, readable format with deduplication and normalization.
    """
    response_lines = [f"Recommended Drugs for {disease.strip().title()}:\n"]
    normalized_seen = set()

    for i, (drug_name, sections) in enumerate(drug_data.items()):
        # Normalize drug name to avoid duplicates like "Anti Itch" and "Anti-Itch"
        normalized_name = drug_name.lower().replace("-", "").replace(" ", "")
        if normalized_name in normalized_seen:
            continue
        normalized_seen.add(normalized_name)

        # Combine all text from the drug's description sections
        raw_text = ""
        for val in sections.values():
            if isinstance(val, list):
                val = " ".join(val)
            raw_text += f" {val}"

        # Clean up text
        cleaned = re.sub(r'\s+', ' ', raw_text).strip()
        cleaned = re.sub(r'\\u[0-9a-fA-F]{4}', '', cleaned)  # Remove Unicode placeholders
        cleaned = cleaned.replace('\u0010', '').replace('\u00051', '')
        cleaned = cleaned.replace("•", "").replace("􀁑", "-")  # Replace symbols
        cleaned = remove_duplicate_sentences(cleaned)  # ✅ Remove duplicate sentences
        cleaned = cleaned[:500]  # Truncate long text

        # Add to response
        response_lines.append(f"{len(response_lines)}. **{drug_name.title()}**\n   - {cleaned}\n")

        if len(response_lines) >= 4:  # Only show top 3 (first line is title)
            break

    return "\n".join(response_lines)

def match_drug_relevance(drug_data, symptoms):
    """
    Scores and ranks drugs based on how many symptoms they mention in their descriptions.
    """
    drug_scores = {}

    for drug_name, sections in drug_data.items():
        # Extract full text of drug description (concatenating all relevant sections)
        raw_text = ""

        for key, value in sections.items():
            if isinstance(value, list):  
                value = " ".join(value)  # ✅ Convert lists to a single string
            raw_text += f" {value}"  

        # Normalize text (remove extra spaces & special chars)
        cleaned_text = re.sub(r'\s+', ' ', raw_text).lower()

        # Count symptom matches
        symptom_count = sum(1 for symptom in symptoms if symptom.lower() in cleaned_text)

        if symptom_count > 0:
            drug_scores[drug_name] = symptom_count

    # Sort drugs by symptom relevance (descending order)
    sorted_drugs = dict(sorted(drug_scores.items(), key=lambda x: x[1], reverse=True))
    
    return sorted_drugs  # Returns {drug_name: score}


def search_drug_info(predicted_disease, medical_advice_data, cleaned_symptoms):
    """
    Search for drugs relevant to the predicted disease and rank them based on symptom relevance.
    """
    if isinstance(predicted_disease, np.ndarray):
        predicted_disease = predicted_disease[0]

    if not isinstance(predicted_disease, str):
        return "Error: Invalid disease format."

    disease_name = predicted_disease.strip().title()

    if disease_name in medical_advice_data:
        drug_data = medical_advice_data[disease_name]
        
        # Get top 3 most relevant drugs based on symptom matching
        # ranked_drugs = match_drug_relevance(drug_data, cleaned_symptoms)
        top_3_drugs = {k: drug_data[k] for k in list(drug_data.keys())[:3]}
        
        # return format_drug_info(top_3_drugs, disease_name)
        return drug_data

    return {}