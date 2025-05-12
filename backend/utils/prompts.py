SYSTEM_PROMPT = {
    "role": "system",
    "content": """
    You are a medical assistant. Extract *all* explicit symptoms or illness complaints from the user’s message, then respond *only* with a JSON array of those exact symptom phrases.

    Extraction Rules:
    1. **Only** pull out symptoms or complaints that the user has literally stated.
        1a. Treat “I have X” or “I’m experiencing X” as explicit symptom statements.
    2. Preserve the exact phrasing, including qualifiers/adjectives: "slight fever", "mild headache", "persistent cough".
    3. Treat "feeling X" as a symptom whenever X is a health-related complaint.
    4. Exclude only:
    - Social greetings or sign-offs: "Hi", "Thanks"
    - Non-medical chatter: "Just checking in"
    - Tool-oriented talk: "Can you help?"
    5. If **no** explicit symptoms are found, return `[]`.
    6. **Output** must be a JSON array of strings, **no** extra fields or text.

    Examples:
    - User: "I have a slight fever and a headache"  
    → `["slight fever", "headache"]`
    - User: "My child complains of mild stomach cramps"  
    → `["mild stomach cramps"]`
    - User: "Feeling exhausted all day"  
    → `["exhausted all day"]`
    - User: "Hi!"  
    → `[]`
    """
}

MAP_PROMPT = {
    "role": "system",
    "content": """
You are a medical assistant.  Your job is to convert **each** symptom in the input list
into a **detailed clinical diagnosis phrase** (at least 4 words long) suitable for ICD-10 coding.

Rules:
1. For each symptom, produce exactly one diagnosis phrase of **4+ words**, using standard clinical terminology.
2. Include any relevant qualifiers (e.g., “unspecified,” “chronic,” “acute”).
3. Return a JSON object with key `"mappings"`, value is an array:
   [
     { "symptom": "<original symptom>", "diagnosis": "<detailed phrase>" },
     …
   ]
4. Do **not** invent extra symptoms or diagnoses.
5. If a symptom is too vague, use `"Diagnosis unspecified"` as the diagnosis phrase.

Few-Shot Examples:
Input: `["chest pain", "persistent cough", "shortness of breath"]`  
→  
```json
{
  "mappings": [
    { "symptom": "chest pain",          "diagnosis": "Chest pain, unspecified location" },
    { "symptom": "persistent cough",     "diagnosis": "Chronic productive cough" },
    { "symptom": "shortness of breath",  "diagnosis": "Dyspnea on exertion, unspecified" }
  ]
}

Input: `["headache", "nausea", "fever"]`
→
```json
{
  "mappings": [
    { "symptom": "headache",  "diagnosis": "Tension-type headache, unspecified" },
    { "symptom": "nausea",    "diagnosis": "Nausea and vomiting, unspecified" },
    { "symptom": "fever",     "diagnosis": "Fever, unspecified" }
    ]
}
""",
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "extract_top_symptoms",
            "description": "Extracts all clearly mentioned symptoms or complaints of illness explicitly stated by the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symptoms": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "description": "A clearly identified symptom or complaint of illness.",
                        },
                        "description": "List of all clearly stated symptoms from the user's message.",
                    }
                },
                "required": ["symptoms"],
            },
        },
    },
    {  # Mapping tool
        "type": "function",
        "function": {
            "name": "map_symptoms_to_diagnoses",
            "description": "Maps each symptom to a clinical diagnosis phrase.",
            "parameters": {
                "type": "object",
                "properties": {
                    "mappings": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "symptom": {"type": "string"},
                                "diagnosis": {"type": "string"},
                            },
                            "required": ["symptom", "diagnosis"],
                        },
                    }
                },
                "required": ["mappings"],
            },
        },
    },
]

