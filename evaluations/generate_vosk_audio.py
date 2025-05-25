import os
from pathlib import Path
from subprocess import run, CalledProcessError
from pydub import AudioSegment

# Configuration
TRANSCRIPT_FILE = "testData.txt"  # Make sure it's in the same folder
OUTPUT_DIR = "tmp_wav_outputs"
FINAL_OUTPUT = "conversation_full.wav"

def parse_transcript(file_path):
    dialogues = []
    doctor_count = 0
    patient_count = 0

    with open(file_path, "r") as file:
        for line in file:
            line = line.strip()
            if line.startswith("P:") or line.startswith("D:"):
                speaker = "Patient" if line.startswith("P:") else "Doctor"
                text = line[2:].strip()
                dialogues.append((speaker, text))
                if speaker == "Doctor":
                    doctor_count += 1
                else:
                    patient_count += 1

    print(f"✔ Total lines: {len(dialogues)}")
    print(f"🩺 Doctor lines: {doctor_count}")
    print(f"🧑‍⚕️ Patient lines: {patient_count}")
    return dialogues

def generate_audio(dialogues, output_dir):
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    logs = []

    for idx, (speaker, text) in enumerate(dialogues):
        voice = "en-us+f3" if speaker == "Doctor" else "en-us+m1"
        filename = f"line_{idx:03}_{speaker}.wav"
        output_path = os.path.join(output_dir, filename)

        try:
            run([
                "espeak-ng",
                "-v", voice,
                "-s", "140",           # Speed
                "-w", output_path,
                text
            ], check=True)
            logs.append(f"[OK] {filename}: {text[:60]}...")
        except CalledProcessError as e:
            logs.append(f"[ERROR] {filename}: {e}")

    with open("tts_generation_log.txt", "w") as log_file:
        log_file.write("\n".join(logs))

    print(f"📁 Audio files saved in: {output_dir}")
    print("📝 Log saved as: tts_generation_log.txt")

def combine_wav_files(input_dir, output_path):
    print("🔊 Combining audio files...")
    combined = AudioSegment.empty()
    for wav_file in sorted(Path(input_dir).glob("*.wav")):
        combined += AudioSegment.from_wav(wav_file)
    combined.export(output_path, format="wav")
    print(f"✅ Final audio saved as: {output_path}")

if __name__ == "__main__":
    dialogues = parse_transcript(TRANSCRIPT_FILE)
    generate_audio(dialogues, OUTPUT_DIR)
    combine_wav_files(OUTPUT_DIR, FINAL_OUTPUT)
    print("🎉 All done! Check the output files.")