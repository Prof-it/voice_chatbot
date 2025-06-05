from typing import List, Dict, Any
import os
import re
import json
import logging
from pathlib import Path
from typing import List, Tuple, Dict, Any

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 1.  Build ICD‑10 TF‑IDF index once at startup
# ---------------------------------------------------------------------------
ICD_CACHE_DIR  = os.path.join(os.path.dirname(__file__),"..", "data")
ICD_DF: pd.DataFrame = pd.read_csv(os.path.join(ICD_CACHE_DIR, "icd10_symptoms.csv"))


_symptom_texts: List[str] = ICD_DF["symptoms"].fillna("").tolist()
_icd_codes: List[str] = ICD_DF["icd10code"].tolist()

_vectorizer = TfidfVectorizer()
_TFIDF_MATRIX = _vectorizer.fit_transform(_symptom_texts)

# Allowed chapters for triage bot (Symptoms + Cardio + Resp.)
_ALLOWED_PREFIXES = ("R", "I", "J")


def retrieve_icd10_filtered(query: str, top_k: int = 5) -> List[Tuple[str, float]]:
    """Return top‑k (code, similarity) filtered by prefix."""
    vec = _vectorizer.transform([query])
    sims = cosine_similarity(vec, _TFIDF_MATRIX).flatten()
    idx_sorted = sims.argsort()[::-1]
    results = []
    for idx in idx_sorted:
        code: str = _icd_codes[idx]
        if not code.startswith(_ALLOWED_PREFIXES):
            continue
        results.append((code, float(sims[idx])))
        if len(results) == top_k:
            break
    return results

# ---------------------------------------------------------------------------
# 2.  Simple ICD‑10 → specialty map (extend as needed)
# ---------------------------------------------------------------------------
_SPECIALTY_MAP = {
    "R": "General Medicine",
    "I": "Cardiology",
    "J": "Pulmonology / Respiratory",
}

def assign_specialty(icd_code: str) -> str:
    """Return specialty based on ICD‑10 chapter letter."""
    if not icd_code:
        return "General Medicine"
    chapter = icd_code[0]
    return _SPECIALTY_MAP.get(chapter, "General Medicine")

# ---------------------------------------------------------------------------
# 3.  Helper to tidy LLaMA symptom strings before retrieval
# ---------------------------------------------------------------------------
_RE_CLEAN = re.compile(r"[^a-zA-Z0-9\s]+")

def clean_symptom(text: str) -> str:
    return _RE_CLEAN.sub(" ", text).lower().strip()

# ---------------------------------------------------------------------------
# 4.  New function to map list[str] symptoms → ICD‑10 + specialty
# ---------------------------------------------------------------------------

def map_symptoms(symptoms: List[str]) -> List[Dict[str, Any]]:
    """Return list of dicts with ICD‑10 suggestions + specialty."""
    output = []
    for s in symptoms:
        clean = clean_symptom(s)
        matches = retrieve_icd10_filtered(clean, top_k=3)
        if matches:
            code, score = matches[0]  # take best
        else:
            code, score = None, 0.0
        output.append({
            "label": s,
            "icd10_candidates": matches,
            "icd10_code": code,
            "similarity": score,
            "specialty": assign_specialty(code)
        })
    return output

def final_session_specialty(mapped: List[Dict[str, Any]]) -> str:
    """Select a single specialty for the encounter.

    Logic:
        1. Highest‑similarity ICD among all symptoms wins.
        2. Break ties by priority: Cardiology > Pulmonology > General.
    """
    if not mapped:
        return "General / Internal Medicine"

    # tie‑break priorities
    priority = {"Cardiology": 3, "Pulmonology / Respiratory": 2, "General / Internal Medicine": 1}

    # find best
    best_item = max(
        mapped,
        key=lambda d: (d["similarity"], priority.get(d["specialty"], 0))
    )
    return best_item["specialty"]