
import os
import pandas as pd
import httpx
import asyncio
from pathlib import Path
from jiwer import compute_measures, cer
from jiwer import Compose, ToLowerCase, RemovePunctuation, RemoveMultipleSpaces, RemoveWhiteSpace, RemoveEmptyStrings



TRANSCRIPT_FILE = "testData.txt"
AUDIO_DIR = "tmp_xtts_wavs"
API_URL = "http://localhost:8000/transcribe_vosk"

# Create a text normalization pipeline
normalizer = Compose([
    ToLowerCase(),
    RemovePunctuation(),
    RemoveMultipleSpaces(),
    RemoveWhiteSpace(replace_by_space=True),
    RemoveEmptyStrings()
])


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
                current_text.append(line.strip())

    if current_speaker and current_text:
        full_lines.append((current_speaker, " ".join(current_text)))

    return full_lines

async def transcribe_and_compare():
    transcript_lines = load_transcript_with_continuation(TRANSCRIPT_FILE)
    audio_files = sorted(Path(AUDIO_DIR).glob("*.wav"))
    results = []

    async with httpx.AsyncClient(timeout=60.0) as client:
        for file in audio_files:
            print(f"🔎 Processing {file.name}...")

            # if file.name > "turn_259_D.wav" :
            #     break
            # idx = int(file.stem.split("_")[1])
            # if idx < 871 or idx > 2553:
            #     continue
            # if file.name < "turn_871_P.wav" or file.name > "turn_2553_P.wav":
            #     continue

            if not file.exists():
                print(f"⚠️ Skipping {file.name}: file not found.")
                continue    

            idx = int(file.stem.split("_")[1])
            if idx >= len(transcript_lines):
                print(f"⚠️ Skipping {file.name}: index {idx} out of range in transcript.")
                continue

            expected_text = transcript_lines[idx][1].strip()

            with open(file, "rb") as f:
                files = {"file": (file.name, f, "audio/wav")}
                try:
                    response = await client.post(API_URL, files=files)
                    if response.status_code == 200:
                        actual_text = response.json().get("text", "").strip() or "[EMPTY]"

                        # Normalize both expected and actual text
                        expected_text_norm = normalizer(expected_text)
                        actual_text_norm = normalizer(actual_text)
                        print(f"[{file.name}] Expected: {expected_text_norm}")
                        print(f"[{file.name}] Actual: {actual_text_norm}")

                        metrics = compute_measures(expected_text_norm, actual_text_norm)
                        cer_value = cer(expected_text_norm, actual_text_norm)
                        print(f"[{file.name}] Metrics: {metrics}")

                        results.append({
                            "file": file.name,
                            "expected": expected_text,
                            "transcribed": actual_text,
                            "expected_norm": expected_text_norm,
                            "transcribed_norm": actual_text_norm,
                            "cer": cer_value,
                            **metrics
                        })
                    else:
                        print(f"[{file.name}] ❌ HTTP {response.status_code} - {response.text}")

                    # Save intermediate results after each file
                    df = pd.DataFrame(results)
                    df.to_csv("transcription_results_871_to_2553.csv", index=False)
                except Exception as e:
                    print(f"[{file.name}] ❌ Error: {e}")

    return results

if __name__ == "__main__":
    asyncio.run(transcribe_and_compare())
