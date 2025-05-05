import sys
import os
import tempfile
import logging
import traceback
from io import BytesIO
from dotenv import load_dotenv
from fastapi import APIRouter, UploadFile, File, HTTPException
from faster_whisper import WhisperModel
from utils.convert_to_wav import convert_to_wav_bytes
from openai import AsyncOpenAI

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.DEBUG)  # Debug logging enabled


model = WhisperModel("base.en", compute_type="int8", download_root="./models")

# Load OpenAI API Key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("Missing OpenAI API key in environment variables.")

# Initialize OpenAI Client (Async)
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# FastAPI Router
transcribe_router = APIRouter()


@transcribe_router.post("/transcribe_openai")
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


@transcribe_router.post("/transcribe")
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

            segments, _ = model.transcribe(temp_wav.name)

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
