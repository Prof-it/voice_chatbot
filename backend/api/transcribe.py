import sys
import os
import json
import wave
import tempfile
import logging
import traceback
from io import BytesIO
from dotenv import load_dotenv
from fastapi import APIRouter, UploadFile, File, HTTPException
from faster_whisper import WhisperModel
from utils.convert_to_wav import convert_to_wav_bytes
from openai import AsyncOpenAI
from vosk import Model as VoskModel, KaldiRecognizer  # type: ignore

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)  # Debug logging enabled


whisper_model = WhisperModel("base.en", compute_type="int8", download_root="./models")
# Load Vosk model if available
vosk_model = VoskModel("./models/vosk-model-small-en-us-0.15")

# Load OpenAI API Key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("Missing OpenAI API key in environment variables.")

# Initialize OpenAI Client (Async)
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# FastAPI Router
transcribe_router = APIRouter()


@transcribe_router.post("/transcribe_openai_whisper")
async def transcribe_audio_openai(file: UploadFile = File(...)):
    """
    Accepts audio file and returns Whisper transcription without disk I/O.
    """
    try:
        audio_bytes = await file.read()

        audio_buffer = BytesIO(audio_bytes)
        audio_buffer.name = file.filename  # Whisper API expects filename attribute

        transcript = await client.audio.transcriptions.create(
            model="whisper-1", file=audio_buffer, response_format="text", language="en"
        )

        print(f"Transcription result: {transcript}")

        logging.debug(f"Transcription result: {transcript}")

        return {"text": transcript}

    except Exception as e:
        logging.error(f"Transcription error: {e}")
        raise HTTPException(status_code=500, detail="Transcription failed.")


@transcribe_router.post("/transcribe_faster_whisper")
async def transcribe_audio(file: UploadFile = File(...)):
    """
    Accepts audio file and returns transcription using faster-whisper.
    """
    try:
        # Read audio file bytes
        file_bytes = await file.read()

        print(f"Received file: {file.filename}, size: {len(file_bytes)} bytes")

        # Convert to WAV using ffmpeg in memory
        wav_bytes = convert_to_wav_bytes(file_bytes)

        # Save to temporary file for model input
        with tempfile.NamedTemporaryFile(suffix=".wav") as temp_wav:
            temp_wav.write(wav_bytes)
            temp_wav.flush()

            segments, _ = whisper_model.transcribe(temp_wav.name)

            # ---------------------- FIX START -------------------------
            # Limit to first 5 unique segments to avoid repetitive output
            unique_texts = []
            for seg in segments:
                if seg.text not in unique_texts:
                    unique_texts.append(seg.text)
                if len(unique_texts) >= 5:
                    break

            transcription = " ".join(unique_texts)
            print("Faster Whisper transcription result:", transcription)
            # ---------------------- FIX END ---------------------------

        return {"text": transcription}

    except Exception as e:
        logging.error(f"Transcription failed: {e}")
        logging.error(traceback.format_exc())
        traceback.print_exc(file=sys.stdout)
        raise HTTPException(status_code=500, detail="Transcription failed.")

# ---------------------------------------------------------------------------
# Vosk endpoint – tiny, fully offline.
# ---------------------------------------------------------------------------
@transcribe_router.post("/transcribe_vosk")
async def transcribe_audio_vosk(file: UploadFile = File(...)):
    """Transcribe audio with Vosk small model (offline)."""
    try:
        file_bytes = await file.read()
        wav_bytes = convert_to_wav_bytes(file_bytes)

        # Vosk expects streaming chunks; wrap BytesIO in wave reader.
        wf = wave.open(BytesIO(wav_bytes), "rb")
        if wf.getnchannels() != 1 or wf.getsampwidth() != 2:
            raise HTTPException(status_code=400, detail="Audio must be mono 16‑bit PCM after conversion.")

        recognizer = KaldiRecognizer(vosk_model, wf.getframerate())
        recognizer.SetWords(True)

        # Read in 4000‑frame chunks (~0.25 s at 16 kHz) for latency balance.
        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            recognizer.AcceptWaveform(data)
        result = json.loads(recognizer.FinalResult())
        text = result.get("text", "")
        logging.debug("Vosk transcription: %s", text)
        return {"text": text}
    except HTTPException:
        raise  # pass through
    except Exception as e:
        logging.error("Vosk transcription failed: %s", e)
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Transcription failed.")

from fastapi.responses import StreamingResponse
import json


@transcribe_router.post("/stream_transcribe_vosk")
async def stream_transcribe_vosk(file: UploadFile = File(...)):
    logging.info("Received file: %s", file.filename)

    try:
        from io import BytesIO

        file_bytes = await file.read()
        wav_file = BytesIO(file_bytes)
        wf = wave.open(wav_file, "rb")
        
        recognizer = KaldiRecognizer(vosk_model, wf.getframerate())
        recognizer.SetWords(True)

        def stream():
            chunk_count = 0
            while True:
                data = wf.readframes(4000)
                if not data:
                    break
                chunk_count += 1
                if recognizer.AcceptWaveform(data):
                    text = json.loads(recognizer.Result()).get("text", "")
                    logging.info(f"Chunk {chunk_count} → Final: {text}")
                    yield f"data: {text}\\n\\n"
                else:
                    partial = json.loads(recognizer.PartialResult()).get("partial", "")
                    if partial:
                        logging.info(f"Chunk {chunk_count} → Partial: {partial}")
                        yield f"data: {partial}\\n\\n"

            final = json.loads(recognizer.FinalResult()).get("text", "")
            logging.info("Final segment: %s", final)
            yield f"data: {final}\\n\\n"

        return StreamingResponse(stream(), media_type="text/event-stream")

    except Exception as e:
        logging.error("Transcription error: %s", str(e))
        raise HTTPException(status_code=500, detail="Streaming failed")
