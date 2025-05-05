import pytest
from httpx import AsyncClient
from fastapi import status
from main import app
import io
import wave


from unittest.mock import AsyncMock, patch
import io

# Create a dummy audio byte stream (just random bytes for testing)
@pytest.fixture
def dummy_audio_file():
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16 bits per sample
        wf.setframerate(16000)
        wf.writeframes(b'\x00\x00' * 16000)  # 1 second of silence
    buffer.seek(0)
    return buffer, "test_audio.wav"


@pytest.mark.asyncio
async def test_transcribe_openai_success(dummy_audio_file):
    audio_data, filename = dummy_audio_file

    # Patch the OpenAI client's transcriptions.create method
    with patch("api.transcribe.client.audio.transcriptions.create", new_callable=AsyncMock) as mock_transcribe:
        mock_transcribe.return_value = "Test transcription from OpenAI."

        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post(
                "/transcribe_openai",
                files={"file": (filename, audio_data, "audio/mpeg")}
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"text": "Test transcription from OpenAI."}


@pytest.mark.asyncio
async def test_transcribe_success(dummy_audio_file):
    audio_data, filename = dummy_audio_file

    # Patch the model.transcribe method
    with patch("api.transcribe.model.transcribe") as mock_model:
        mock_model.return_value = ([type("Segment", (object,), {"text": "Mock transcription"})()], None)

        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post(
                "/transcribe",
                files={"file": (filename, audio_data, "audio/mpeg")}
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"text": "Mock transcription"}


@pytest.mark.asyncio
async def test_transcribe_openai_no_file():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/transcribe_openai", files={})

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY  # FastAPI throws this when required file is missing


@pytest.mark.asyncio
async def test_transcribe_no_file():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/transcribe", files={})

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.fixture
def real_audio_file():
    filename = "hello-what-you-doing-42455.mp3"
    with open(f"./{filename}", "rb") as f:
        return io.BytesIO(f.read()), filename


@pytest.mark.asyncio
async def test_transcribe_openai_real_audio(real_audio_file):
    audio_data, filename = real_audio_file

    # No mocking — this will actually call OpenAI Whisper
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/transcribe_openai",
            files={"file": (filename, audio_data, "audio/wav")}
        )

    assert response.status_code == 200
    result = response.json()
    assert "text" in result
    print("OpenAI transcription result:", result["text"])


@pytest.mark.asyncio
async def test_transcribe_faster_whisper_real_audio(real_audio_file):
    audio_data, filename = real_audio_file

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/transcribe",
            files={"file": (filename, audio_data, "audio/wav")}
        )

    assert response.status_code == 200
    result = response.json()
    assert "text" in result
    print("Faster Whisper transcription result:", result["text"])

    text = result["text"]
    # Assert there's some transcription
    assert len(text.strip()) > 0

    # Assert no more than 5 unique sentences
    sentences = [s.strip() for s in text.split("?") if s.strip()]
    assert len(sentences) <= 5
