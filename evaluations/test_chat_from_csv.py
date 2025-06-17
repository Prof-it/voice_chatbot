import asyncio
import httpx
import json
import pandas as pd
from pathlib import Path
import logging
# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

TRANSCRIPT_FILE = "syntheticData.txt"
API_URL = "http://localhost:8000/chat"
OUTPUT_CSV = "LLM_symptom_extractions_13062025_1.csv"

def load_transcript_with_continuation(file_path):
    full_lines = []
    current_speaker = None
    current_text = []

    with open(file_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            if line.startswith("P:") or line.startswith("D:"):
                if current_speaker and current_text:
                    full_lines.append((current_speaker, " ".join(current_text)))
                current_speaker = "P" if line.startswith("P:") else "D"
                current_text = [line[2:].strip()]
            else:
                current_text.append(line)

    if current_speaker and current_text:
        full_lines.append((current_speaker, " ".join(current_text)))

    return full_lines

async def get_accumulated_symptoms(utterance: str, prev_acc: list) -> list:
    """
    Sends the user utterance plus previous accumulated_symptoms
    to the /chat endpoint, streams the SSE, and returns the
    updated accumulated_symptoms from the final_metadata frame.
    """
    payload = {
        "messages": [{"role": "user", "content": utterance}],
        "accumulated_symptoms": prev_acc
    }
    accumulated = prev_acc[:]  # start from previous

    async with httpx.AsyncClient(timeout=600.0) as client:
        async with client.stream("POST", API_URL, json=payload) as resp:
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                body = line[len("data: "):].strip()

                logging.info(f"Received line: {body}")
                # break on DONE marker
                if body == "[DONE]":
                    break

                # try parse JSON
                try:
                    data = json.loads(body)
                except json.JSONDecodeError:
                    logging.info(f"Failed to parse JSON from line: {body}")
                    continue

                # update accumulated if metadata
                if isinstance(data, dict) and data.get("type") == "final_metadata":
                    accumulated = data.get("accumulated_symptoms", [])
    return accumulated

async def main():
    transcript = load_transcript_with_continuation(TRANSCRIPT_FILE)
    results = []
    accumulated = []  # carry this forward between calls

    # only first 10 patient turns
    count = 0
    for speaker, utterance in transcript:
        if speaker != "P":
            continue    

        logging.info(f"Processing utterance: {utterance}")
        # pass along the previous accumulated list
        new_accumulated = await get_accumulated_symptoms(utterance, [])
        results.append({
            "utterance": utterance,
            "llm_actual": new_accumulated
        })
        count += 1
        print(f"[{count}] Extracted: {new_accumulated}")

        if count >= 10:
            break

    # write CSV
    df = pd.DataFrame(results)
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"\n✅ Saved to '{OUTPUT_CSV}'")

if __name__ == "__main__":
    asyncio.run(main())
