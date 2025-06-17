import pandas as pd
from typing import List
from trulens_eval import Tru, Feedback
from trulens_eval.tru_custom_app import TruCustomApp
import ast

# ---------------------------
# Load and Prepare the Data
# ---------------------------
df = pd.read_csv("LLM_predicted_symptoms.csv")

# Convert string lists to actual lists and normalize
df['llm_predicted'] = df['llm_predicted'].apply(lambda x: list(map(str.lower, ast.literal_eval(x))))
df['actual_output'] = df['actual_output'].apply(lambda x: list(map(str.lower, ast.literal_eval(x))))

# Sample a small set for evaluation (can increase later)
sample_df = df.sample(10, random_state=42).copy()

# ---------------------------
# Simulate the LLM Function
# ---------------------------
def mock_symptom_extractor(utterance: str) -> List[str]:
    return sample_df.loc[sample_df['utterance'] == utterance, 'llm_predicted'].values[0]

# Wrap it for TruLens
app = TruCustomApp(app=mock_symptom_extractor)

# ---------------------------
# Feedback Function
# ---------------------------
def jaccard_feedback(predicted: List[str], reference: List[str]) -> float:
    a, b = set(predicted), set(reference)
    return len(a & b) / len(a | b) if a or b else 1.0

feedback = Feedback(jaccard_feedback, name="Symptom Jaccard Match")

# ---------------------------
# Evaluation with TruLens
# ---------------------------
tru = Tru()
tru.reset_database()

records = []
for _, row in sample_df.iterrows():
    result = app.app(row["utterance"])  # use direct function call
    record = {
        "input": row["utterance"],
        "output": result,
        "reference": row["actual_output"]
    }
    records.append(record)

# tru.

# ---------------------------
# Print Results
# ---------------------------
print("\n=== Evaluation Results ===\n")
for r in records:
    print(f"Utterance: {r['input']}")
    print(f"Predicted: {r['output']}")
    print(f"Reference: {r['reference']}")
    print(f"Jaccard Score: {jaccard_feedback(r['output'], r['reference']):.2f}")
    print("-" * 40)

# Optional: Launch local dashboard
tru.run_dashboard()  # Uncomment if you want to explore via web UI
