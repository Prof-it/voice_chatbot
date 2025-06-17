
import torch
from TTS.api import TTS
from pydub import AudioSegment
import os
from pathlib import Path

# Device check
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"🖥️ Using device: {device}")

# Load XTTS model
print("🔊 Loading XTTS model...")
try:
    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
    print("✅ XTTS model loaded.")
except Exception as e:
    print(f"❌ Error loading TTS model: {e}")
    exit()

# Speaker Mapping
speaker_map_internal_ids = {
    "P": "Gilberto Mathias",   # European Male
    "D": "Gitta Nikolina"      # Female Doctor
}

# Paths
transcript_path = "syntheticData.txt"
temp_dir = Path("tmp_xtts_wavs")
output_conversation_path = "conversation_xtts.wav"
temp_dir.mkdir(parents=True, exist_ok=True)

# Custom parser to handle line continuations
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

# Load combined lines
lines = load_transcript_with_continuation(transcript_path)
doctor_lines = sum(1 for line in lines if line[0] == "D")
patient_lines = sum(1 for line in lines if line[0] == "P")
print(f"📋 Parsed {len(lines)} lines — Doctor: {doctor_lines}, Patient: {patient_lines}")

# Build conversation
conversation = AudioSegment.silent(duration=0)
logs = []

start_index = 0  # Resume from here
for idx, (spk_char, txt) in enumerate(lines[start_index:], start=start_index):
    speaker_name = speaker_map_internal_ids.get(spk_char)
    filename = temp_dir / f"turn_{idx:03}_{spk_char}.wav"

    if filename.exists():
        print(f"⏭️ Skipping already generated file: {filename.name}")
        continue

    try:
        if speaker_name:
            print(f"🔈 [{idx}] {spk_char}: {txt[:60]}...")
            tts.tts_to_file(text=txt, speaker=speaker_name, language="en", file_path=str(filename))
            logs.append(f"[OK] {idx} {spk_char} ({speaker_name}): {txt[:60]}...")
        else:
            print(f"⚠️ [{idx}] Speaker '{spk_char}' not mapped, using XTTS default.")
            tts.tts_to_file(text=txt, language="en", file_path=str(filename))
            logs.append(f"[WARN] {idx} {spk_char}: Used default XTTS voice")

        segment = AudioSegment.from_wav(filename)
        conversation += segment + AudioSegment.silent(duration=300)

    except Exception as e:
        print(f"❌ Error at line {idx}: {e}")
        logs.append(f"[ERROR] {idx} {spk_char}: {e}")

# Export final conversation
if len(conversation) > 0:
    try:
        conversation.export(output_conversation_path, format="wav")
        print(f"\n✅ Final conversation exported: {output_conversation_path}")
    except Exception as e:
        print(f"❌ Error exporting final conversation: {e}")
else:
    print("⚠️ No audio segments generated.")

with open("tts_generation_log.txt", "w") as f:
    f.write("\n".join(logs))

print("📄 Logs saved to tts_generation_log.txt")
print("✅ Done.")
