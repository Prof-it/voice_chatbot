import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
from api.chat import chat_router
from main import app  # Or wherever you mount chat_router
from utils.types import ChatRequest
from types import SimpleNamespace

app.include_router(chat_router)


@pytest.fixture
def dummy_chat_request():
    return ChatRequest(
        messages=[{"role": "user", "content": "I have a headache and feel dizzy."}],
        accumulated_symptoms=[],
    )


@pytest.mark.asyncio
async def test_chat_success(dummy_chat_request):
    # Mock ICD-10 model and tokenizer
    app.state.icd10 = {
        "model": "mock_model",
        "tokenizer": "mock_tokenizer",
        "device": "cpu",
    }

    with patch(
        "api.chat.client.chat.completions.create", new_callable=AsyncMock
    ) as mock_create, patch("api.chat.predict_icd10") as mock_predict_icd10, patch(
        "api.chat.map_icd10_to_specialties"
    ) as mock_map_specialties:

        # Mock OpenAI response for streaming
        mock_stream_response = AsyncMock()


        mock_stream_response.__aiter__.return_value = [
            SimpleNamespace(
                id="chatcmpl-mockid",
                object="chat.completion.chunk",
                created=123456,
                model="gpt-4-turbo",
                system_fingerprint="abc123",
                choices=[
                    SimpleNamespace(
                        index=0,
                        delta=SimpleNamespace(
                            content="Based on your symptoms, here are possible conditions.",
                            tool_calls=None,
                        ),
                        finish_reason="stop",
                    )
                ],
            )
        ]
        mock_create.return_value = mock_stream_response

        # Mock ICD-10 prediction and specialty mapping
        mock_predict_icd10.return_value = [{"icd10": "R51", "score": 0.95}]
        mock_map_specialties.return_value = ["Neurology"]

        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post("/chat", json=dummy_chat_request.dict())

            assert response.status_code == 200
            # Because it's a streaming response, collect the stream into text
            chunks = [line.decode() for line in response.iter_bytes()]
            print("Streamed response:", chunks)
            assert any("Based on your symptoms" in c for c in chunks)
