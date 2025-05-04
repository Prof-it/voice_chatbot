import logging
import torch

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def predict_icd10(symptoms: list[str], tokenizer, model, device):
    """
    Map each symptom to an ICD-10 code.
    """
    results = []
    model.eval()
    for symptom in symptoms:
        inputs = tokenizer(symptom, return_tensors="pt", truncation=True)
        inputs = {k: v.to(device) for k, v in inputs.items()}
        with torch.no_grad():
            outputs = model(**inputs)
        pred_idx = int(torch.argmax(outputs.logits, dim=-1))
        icd_code = model.config.id2label[pred_idx]
        results.append({"symptom": symptom, "icd10": icd_code})
    return results

def map_icd10_to_specialties(icd10_codes: list[str]) -> str:
    """
    Maps ICD-10 codes to the most likely medical specialty.
    Chooses highest count and prioritizes certain specialties.
    """
    icd_specialty_map = {
        "A": "Infectious Diseases",
        "B": "Infectious Diseases",
        "C": "Oncology",
        "D": "Hematology / Oncology",
        "E": "Endocrinology",
        "F": "Psychiatry",
        "G": "Neurology",
        "H": "Otolaryngology (ENT) / Ophthalmology",
        "I": "Cardiology",
        "J": "Pulmonology / ENT",
        "K": "Gastroenterology",
        "L": "Dermatology",
        "M": "Orthopedics / Rheumatology",
        "N": "Nephrology / Urology",
        "O": "Obstetrics / Gynecology",
        "P": "Pediatrics",
        "Q": "Genetics / Pediatrics",
        "R": "General Practice / Diagnostics",
        "S": "Orthopedics / Trauma",
        "T": "Orthopedics / Trauma",
        "Z": "Preventive Care / General Practice"
    }

    # Specialty priority (higher index → lower priority)
    specialty_priority = [
        "Otolaryngology (ENT) / Ophthalmology",
        "Pulmonology / ENT",
        "Neurology",
        "Cardiology",
        "Orthopedics / Rheumatology",
        "Gastroenterology",
        "Dermatology",
        "Psychiatry",
        "Hematology / Oncology",
        "Endocrinology",
        "Infectious Diseases",
        "Nephrology / Urology",
        "Obstetrics / Gynecology",
        "Pediatrics",
        "Genetics / Pediatrics",
        "Orthopedics / Trauma",
        "Preventive Care / General Practice",
        "General Practice / Diagnostics"
    ]

    specialty_counts = {}

    for code in icd10_codes:
        if not code:
            continue
        chapter = code[0].upper()
        specialty = icd_specialty_map.get(chapter)
        if specialty:
            specialty_counts[specialty] = specialty_counts.get(specialty, 0) + 1

    if not specialty_counts:
        return "General Practice"

    # Step 1: Find the max count specialties
    max_count = max(specialty_counts.values())
    top_specialties = [spec for spec, count in specialty_counts.items() if count == max_count]

    # Step 2: If only one specialty, return it
    if len(top_specialties) == 1:
        return top_specialties[0]

    # Step 3: Use priority to break tie
    sorted_specialties = sorted(
        top_specialties,
        key=lambda s: specialty_priority.index(s) if s in specialty_priority else len(specialty_priority)
    )

    return sorted_specialties[0]
