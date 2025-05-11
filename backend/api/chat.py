import os
import traceback
import asyncio
import logging
import json
import traceback

from utils.predict import predict_icd10, map_icd10_to_specialties
from utils.prompts import MAP_PROMPT, SYSTEM_PROMPT
from utils.types import ChatRequest


from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from ollama import AsyncClient, ChatResponse
from pydantic import BaseModel, ValidationError
from typing import Literal, Dict, Any, List, AsyncGenerator

# Define the schema for the response
class Symptom(BaseModel):
  name: str

class SymptomsList(BaseModel):
  symptoms: list[Symptom]

class DiagnosisMapping(BaseModel):
    """Represents a single mapping from a symptom phrase to a clinical diagnosis."""
    symptom: str # The symptom phrase used by the LLM for mapping
    diagnosis: str      # The detailed clinical diagnosis phrase from the LLM

class DiagnosesMappingResult(BaseModel):
    """The expected JSON structure for the result of mapping symptoms to diagnoses."""
    mappings: list[DiagnosisMapping]




load_dotenv()

logging.basicConfig(level=logging.INFO)  # Debug logging enabled

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434")
OLLAMA_KEY = os.getenv("OLLAMA_API_KEY", "ollama-openai-api-key")

# Load OpenAI API Key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("Missing OpenAI API key in environment variables.")

# Initialize Ollama Client
client = AsyncClient(
    host=OLLAMA_URL
)

# FastAPI Router
chat_router = APIRouter()

def _create_sse_data_string(
    id_prefix: str,
    model: str,
    role: Literal["system", "user", "assistant", "tool"] = "assistant",
    delta_content: str | None = None,
    finish_reason: str | None = None
) -> str:
    """
    Creates a Server-Sent Event (SSE) data string in a format mimicking OpenAI's API.
    """
    timestamp = int(asyncio.get_event_loop().time())
    # Generate a somewhat unique ID part. For true uniqueness, consider UUIDs.
    random_hex = os.urandom(3).hex()
    chunk_id = f"chatcmpl-{id_prefix}-{random_hex}-{timestamp}"

    delta: Dict[str, Any] = {"role": role}
    if delta_content is not None:
        delta["content"] = delta_content

    # If it's a final chunk with a finish_reason and no new content,
    # OpenAI often sends an empty delta or just the role.
    # Forcing delta to be empty if only finish_reason and no content for this chunk.
    if finish_reason and delta_content is None:
        delta = {} # Ensure delta is empty if it's purely a final marker with no new content

    sse_obj = {
        "id": chunk_id,
        "object": "chat.completion.chunk",
        "created": timestamp,
        "model": model, # Model name from the actual LLM response chunk
        "choices": [
            {
                "index": 0,
                "delta": delta,
                "finish_reason": finish_reason,
            }
        ],
    }
    return f"data: {json.dumps(sse_obj)}\n\n"

async def openai_stream_response(chat_request: ChatRequest, icd10_data: dict):
    user_messages_for_turn = chat_request.messages # Messages from the current user turn
    accumulated_symptoms_str_list = list(chat_request.accumulated_symptoms) # Ensure it's a mutable list

    logging.info(f"Processing request. Accumulated symptoms: {accumulated_symptoms_str_list}")
    logging.info(f"Incoming messages for this turn: {user_messages_for_turn}")

    current_json_accumulator = ""
    symptoms_llm_model_name = "llama3.2:1b" # Default, can be updated from chunk
    primary_extraction_successful = False
    extracted_symptom_names: List[str] = []

    try:
        # --- Stage 1: Primary Attempt - Symptom Extraction via structured JSON ---
        logging.info("Stage 1: Attempting structured symptom extraction.") 
        symptom_extraction_llm_messages = [
            SYSTEM_PROMPT,
            *user_messages_for_turn
        ]

        symptom_stream: AsyncGenerator[ChatResponse, None] = await client.chat(
            model=symptoms_llm_model_name,
            messages=symptom_extraction_llm_messages,
            format=SymptomsList.model_json_schema(),
            options={'temperature': 0},
            stream=True
        )

        async for chunk in symptom_stream:
            symptoms_llm_model_name = getattr(chunk, 'model', symptoms_llm_model_name)
            message_data = getattr(chunk, 'message', None)
            
            if message_data and (content_part := getattr(message_data, 'content', None)):
                current_json_accumulator += content_part
                # yield _create_sse_data_string("symptom-json", symptoms_llm_model_name, delta_content=content_part)

            if getattr(chunk, 'done', False):
                logging.info(f"Symptom extraction stream finished. Accumulated JSON: '{current_json_accumulator}'")
                symptoms_obj: SymptomsList | None = None
                try:
                    symptoms_obj = SymptomsList.model_validate_json(current_json_accumulator)
                    if symptoms_obj.symptoms and all(hasattr(s, 'name') and s.name for s in symptoms_obj.symptoms):
                        extracted_symptom_names = [s.name for s in symptoms_obj.symptoms if s.name]
                        primary_extraction_successful = True
                        logging.info(f"Successfully parsed and validated symptoms: {extracted_symptom_names}")
                    else:
                        logging.info("Parsed SymptomsList, but it effectively contains no named symptoms.")
                        extracted_symptom_names = [] # Ensure empty list
                        # primary_extraction_successful remains False if list is empty or items lack names
                except (ValidationError, json.JSONDecodeError) as e_parse:
                    logging.error(f"Failed to parse/validate symptoms JSON: '{current_json_accumulator}'. Error: {e_parse}")
                
                finish_reason = "stop" if primary_extraction_successful and extracted_symptom_names else "error"
                yield _create_sse_data_string("symptom-json-done", symptoms_llm_model_name, finish_reason=finish_reason)
                break # Exit symptom extraction stream loop

        # --- Fallback or Proceed Logic ---
        # also check if its the user's first message
        if not primary_extraction_successful and len(user_messages_for_turn) != 1:
            logging.warning("Primary symptom extraction failed or yielded no valid symptoms. Initiating fallback.")
            yield _create_sse_data_string("info", symptoms_llm_model_name, delta_content="I'm having a little trouble pinpointing specific symptoms. Let's try a different approach.")

            fallback_system_prompt = (
                SYSTEM_PROMPT["content"] +
                "Your previous attempt to identify symptoms in a structured way was not successful or found none. "
                "Please respond conversationally to the user. Ask for clarification or how you can help. Avoid JSON output."
            )

            fallback_llm_messages = [{
                'role': 'system',
                'content': fallback_system_prompt
            }, *user_messages_for_turn]
            
            fallback_llm_model_name = "llama3.2:1b" # Reset or use specific model
            fallback_stream: AsyncGenerator[ChatResponse, None] = await client.chat(
                model=fallback_llm_model_name, messages=fallback_llm_messages, options={'temperature': 0.5}, stream=True
            )
            async for fb_chunk in fallback_stream:
                fallback_llm_model_name = getattr(fb_chunk, 'model', fallback_llm_model_name)
                fb_message_data = getattr(fb_chunk, 'message', None)
                if fb_message_data and (fb_content := getattr(fb_message_data, 'content', None)):
                    yield _create_sse_data_string("fallback", fallback_llm_model_name, delta_content=fb_content)
                if getattr(fb_chunk, 'done', False):
                    yield _create_sse_data_string("fallback-done", fallback_llm_model_name, finish_reason="stop")
            yield "data: [DONE]\n\n"
            return # End function after fallback

        # --- Primary Extraction Succeeded: Update accumulated symptoms ---
        new_symptoms = [name for name in extracted_symptom_names if name not in accumulated_symptoms_str_list]
        if new_symptoms:
            accumulated_symptoms_str_list.extend(new_symptoms)
            accumulated_symptoms_str_list = sorted(list(set(accumulated_symptoms_str_list)))
        logging.info(f"Updated accumulated symptoms: {accumulated_symptoms_str_list}")

        # --- Stage 1.5: Conversational Response or Proceed to Stage 2 (Mapping) ---
        final_response_payload: Any # This will hold string or dict for the final SSE content
        current_llm_model_name = symptoms_llm_model_name # Model used for the last successful interaction

        if not accumulated_symptoms_str_list:
            final_response_payload = "Hello! If you have any symptoms or health concerns, please let me know so I can assist you further."
        elif len(accumulated_symptoms_str_list) < 3:
            final_response_payload = (
                f"I understand you're experiencing: {', '.join(accumulated_symptoms_str_list)}. "
                "Could you please tell me about any other symptoms you might have?"
            )
        else:
            # --- Stage 2: Sufficient symptoms, proceed to mapping ---
            logging.info(f"Stage 2: Mapping symptoms to diagnoses for: {accumulated_symptoms_str_list}")
            mapping_llm_model_name = "llama3.2:1b" # Or a dedicated model
            diagnoses_mapping_system_prompt = (
                MAP_PROMPT["content"] +
                f"\nMap the given symptoms: {json.dumps(accumulated_symptoms_str_list)} to clinical diagnoses. "
                f"Respond ONLY with a valid JSON object adhering to this schema: {DiagnosesMappingResult.model_json_schema()}."
            )
            map_llm_messages = [
                {'role': 'system', 'content': diagnoses_mapping_system_prompt},
                {'role': 'user', 'content': f"Provide diagnoses for: {', '.join(accumulated_symptoms_str_list)}."}
            ]

            try:
                map_response_ollama : AsyncGenerator[ChatResponse] = await client.chat(
                    model=mapping_llm_model_name, messages=map_llm_messages, format=DiagnosesMappingResult.model_json_schema(), options={'temperature': 0}
                )
                current_llm_model_name = getattr(map_response_ollama, 'model', mapping_llm_model_name)
                logging.debug(f"Ollama mapping response (raw): {map_response_ollama}")

                diagnoses_obj: DiagnosesMappingResult | None = None
                if map_response_ollama and (map_content := map_response_ollama.get('message', {}).get('content')):
                    diagnoses_obj = DiagnosesMappingResult.model_validate_json(map_content)
                    logging.info(f"Successfully parsed diagnoses mapping: {diagnoses_obj.mappings}")
                
                if diagnoses_obj:
                    detailed_diagnoses = [m.diagnosis for m in diagnoses_obj.mappings if m.diagnosis]
                    icd_10_list = predict_icd10(detailed_diagnoses, icd10_data["tokenizer"], icd10_data["model"], icd10_data["device"])
                    specialty = map_icd10_to_specialties([item.get("icd10") for item in icd_10_list if item.get("icd10")])
                    final_response_payload = {
                        "symptoms": accumulated_symptoms_str_list,
                        "mappings": [m.model_dump() for m in diagnoses_obj.mappings],
                        "detailed_diagnoses": detailed_diagnoses, "icd10": icd_10_list,
                        "appointment": {"specialty": specialty, "suggestedDate": "TBD", "suggestedTime": "TBD"},
                    }
                else: # Failed to get or parse mapping
                    raise ValueError("Failed to obtain or parse diagnoses mapping from LLM.")
            except (ValidationError, json.JSONDecodeError, ValueError) as e_map:
                logging.error(f"Error during Stage 2 (mapping): {e_map}")
                final_response_payload = {
                    "symptoms": accumulated_symptoms_str_list,
                    "error_message": "I identified your symptoms, but encountered an issue providing detailed mappings. Please consult a healthcare professional.",
                    "icd10": [], "appointment": {}
                }
            current_llm_model_name = mapping_llm_model_name # Model used for this stage

        # --- Stage 3: Yield the final response ---
        final_content_str = json.dumps(final_response_payload) if isinstance(final_response_payload, dict) else final_response_payload
        yield _create_sse_data_string("final", current_llm_model_name, delta_content=final_content_str, finish_reason="stop")
        # Optionally, send accumulated_symptoms as separate metadata if client needs it before [DONE]
        yield f"data: {json.dumps({'type': 'final_metadata', 'accumulated_symptoms': accumulated_symptoms_str_list})}\n\n"
        yield "data: [DONE]\n\n"

    except Exception as e:
        logging.error(f"Unhandled error in openai_stream_response: {traceback.format_exc()}")
        # Use the model name from the last known context if possible, else default
        err_model_name = symptoms_llm_model_name # Or a general default
        error_content = f"An unexpected server error occurred: {str(e)}"
        yield _create_sse_data_string("error", err_model_name, delta_content=error_content, finish_reason="error")
        yield "data: [DONE]\n\n"

@chat_router.post("/chat")
async def chat(request: Request, chat_request: ChatRequest):
    """
    This Python function handles POST requests to a chat endpoint, processing chat messages and
    returning a streaming response using OpenAI and ICD-10 data.
    
    :param request: The `request` parameter represents the incoming request to the `/chat` endpoint. It
    contains information about the request such as headers, query parameters, and more
    :type request: Request
    :param chat_request: The `chat_request` parameter in the code snippet represents a data model or
    object that contains information related to a chat request. It likely includes details such as
    messages exchanged in the chat, user information, timestamps, or any other relevant data needed to
    process the chat request. This parameter is used to extract
    :type chat_request: ChatRequest
    :return: A StreamingResponse object is being returned with the openai_stream_response function and
    the ICD-10 data. The media type is set to "text/event-stream".
    """
    messages = chat_request.messages
    icd10 = request.app.state.icd10

    if not messages:
        raise HTTPException(
            status_code=400, detail="Missing 'messages' field in request body."
        )

    return StreamingResponse(
        openai_stream_response(chat_request, icd10),
        media_type="text/event-stream",
    )
