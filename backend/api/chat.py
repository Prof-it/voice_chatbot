import os
import traceback
import asyncio
import logging
import json
import traceback
import psutil

from utils.predict import map_symptoms, final_session_specialty
from utils.prompts import SYMPTOM_PROMPT
from utils.types import ChatRequest

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from ollama import AsyncClient
from pydantic import BaseModel
from typing import Literal, Dict, Any
from fhir.resources.condition import Condition
from fhir.resources.codeableconcept import CodeableConcept

from fhir.resources.appointment import Appointment

from datetime import datetime, timedelta



def log_memory_usage(tag: str = "Memory"):
    process = psutil.Process(os.getpid())
    
    # Current RAM usage
    mem_bytes = process.memory_info().rss
    mem_mb = mem_bytes / (1024 * 1024)

    # Peak RAM usage (Linux/Unix: use `.rss`, Windows: use `.peak_wset`)
    try:
        peak_bytes = process.memory_info().peak_wset  # Windows only
    except AttributeError:
        peak_bytes = getattr(process.memory_info(), 'rss', mem_bytes)  # fallback for Linux
    peak_mb = peak_bytes / (1024 * 1024)

    logging.info(f"{tag} - RAM used: {mem_mb:.2f} MB | Peak: {peak_mb:.2f} MB")


class SymptomDetection(BaseModel):
    detected: bool
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

def symptom_to_fhir_condition(symptom_name: str) -> Condition:
    return Condition.model_construct(
        code=CodeableConcept.model_construct(
            text=symptom_name
        ),
        clinicalStatus={"text": "active"},
        verificationStatus={"text": "unconfirmed"}
    )

def create_fhir_appointment(specialty: str) -> Appointment:

    # datetime string 2 days from now
    start_str = datetime.now() + timedelta(days=2)
    start_str = start_str.strftime("%Y-%m-%dT%H:%M:%S+01:00")
    end_str = datetime.now() + timedelta(days=2, hours=1)
    end_str = end_str.strftime("%Y-%m-%dT%H:%M:%S+01:00")
    
    
    # Create a FHIR Appointment object
    return Appointment.model_construct(
        status="proposed",
        description=f"Appointment for {specialty}",
        start=start_str,
        end=end_str,
    )


load_dotenv()

logging.basicConfig(level=logging.INFO)  # Debug logging enabled

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434")

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

def is_greeting(text: str) -> bool:
    t = text.strip().lower()
    return t in {"hi", "hello", "hey", "good morning", "good afternoon"}

# $SELECTION_PLACEHOLDER$ replacement with logging
async def extract_symptoms_json(messages: list, model: str) -> list[str] | None:
    """
    Attempts to extract symptoms as a JSON array via the LLM.
    Returns the list of symptom strings if VALID, otherwise None.
    """
    logging.info(f"extract_symptoms_json: Starting with model={model}")
    log_memory_usage("Before LLM call")
    accumulator = ""
    stream = await client.chat(
        model=model,
        messages=[SYMPTOM_PROMPT, *messages],
        format=SymptomsList.model_json_schema(),
        options={
        "num_ctx": 128,
        "temperature": 0.0,
    },
        stream=True
    )
    async for chunk in stream:
        logging.info("llm_stream_response: Starting response stream")
        log_memory_usage("During LLM stream")
        logging.debug(f"extract_symptoms_json: Received chunk={chunk}")
        if content := getattr(chunk.message, "content", None):
            accumulator += content
            logging.debug(f"extract_symptoms_json: Accumulator updated to={accumulator!r}")
        if getattr(chunk, "done", False):
            logging.info("extract_symptoms_json: Stream done, validating JSON")
            # 1) quick sanity check
            if not accumulator.strip().startswith("{"):
                logging.warning("extract_symptoms_json: Accumulator does not start with '[' – returning None")
                return []
            # 2) parse + validate
            try:
                obj = SymptomsList.model_validate_json(accumulator)
                names = [s.name for s in obj.symptoms if s.name]
                log_memory_usage("After LLM JSON validation")
                if names:
                    logging.info(f"extract_symptoms_json: Parsed symptoms={names}")
                    return names
                else:
                    logging.warning("extract_symptoms_json: No valid symptom names found – returning None")
                    log_memory_usage("After LLM JSON validation")
                    return []
            except Exception as e:
                logging.error(f"extract_symptoms_json: JSON validation failed: {e}")
                log_memory_usage("After LLM JSON validation")
                return []
        
    

async def fallback_clarify(messages: list):
    logging.info("fallback_clarify: Starting fallback clarification stream")
    prompt = SYMPTOM_PROMPT["content"] + (
        "Your JSON extraction failed. Please ask the user to clarify their symptoms."
    )
    stream = await client.chat(
        model="llama3.2:1b",
        messages=[{"role": "system", "content": prompt}, *messages],
        options={
        "num_ctx": 128,
        # "num_thread": 2,
        # "top_p": 0.9,
        # "repeat_penalty": 1.1,
        "temperature": 0.0,
    },
        stream=True
    )
    async for chunk in stream:
        logging.debug(f"fallback_clarify: Received chunk={chunk}")
        if content := getattr(chunk.message, "content", None):
            logging.info(f"fallback_clarify: Yielding content chunk")
            yield _create_sse_data_string("fallback", chunk.model, delta_content=content)
        if getattr(chunk, "done", False):
            logging.info("fallback_clarify: Stream done, sending fallback-done")
            yield _create_sse_data_string("fallback-done", chunk.model, finish_reason="stop")
    logging.info("fallback_clarify: Sending [DONE]")
    yield "data: [DONE]\n\n"

async def llm_stream_response(chat_request: ChatRequest, icd10_data):
    logging.info("llm_stream_response: Starting response stream")
    msgs = chat_request.messages
    accu = list(chat_request.accumulated_symptoms)
    logging.info(f"llm_stream_response: Initial accumulated_symptoms={accu}")


    user_text = msgs[-1].content if msgs else ""
    logging.info(f"llm_stream_response: User text={user_text!r}")
    logging.info("llm_stream_response: Starting response stream")
    log_memory_usage("Start of stream")

    # 1) Extract
    names = await extract_symptoms_json(msgs, "llama3.2:1b")

    # 2) Merge new
    new = [n for n in names if n not in accu]
    if new:
        logging.info(f"llm_stream_response: New symptoms to add={new}")
        accu += new
        logging.debug(f"llm_stream_response: Updated accumulated_symptoms={accu}")


    # 3) If <3 symptoms, ask for more
    if len(accu) < 3:
        if accu:
            text = (
                f"I understand you're experiencing: {', '.join(accu)}. "
                "Could you please tell me about any other symptoms you might have?"
            )
        else:
            text = "Hi! What symptoms are you experiencing today?"
        logging.info("llm_stream_response: Asking user for more symptoms")
        yield _create_sse_data_string("assistant", "llama3.2:1b", delta_content=text, finish_reason="stop")

        # 2) emit metadata (updated)
        yield f"data: {json.dumps({'type': 'final_metadata', 'accumulated_symptoms': accu})}\n\n"
        yield "data: [DONE]\n\n"
        logging.info("llm_stream_response: Sent metadata and [DONE] after asking for more symptoms")
        return

    # 4) Map to diagnoses
    logging.info(f"llm_stream_response: Proceeding to map {accu} to diagnoses")
    try:
        mappings = map_symptoms(accu)
        specialty = final_session_specialty(mappings)
        logging.info(f"llm_stream_response: Mappings={mappings}, specialty={specialty}")
        icd_10_codes = [
            {
                "icd10": m["icd10_code"],
                "label": m["label"],
             } 
            for m in mappings]
        logging.info(f"llm_stream_response: ICD-10 codes={icd_10_codes}, specialty={specialty}")

        final = {
            "symptoms": accu,
            "mappings": mappings,            
            "icd10": icd_10_codes,
            "appointment": {
                "specialty": specialty,
                "suggestedDate": "TBD",
                "suggestedTime": "TBD"
            },
            "symptoms_fhir": [symptom_to_fhir_condition(s).model_dump() for s in accu],
            "appointment_fhir": create_fhir_appointment(specialty).model_dump(),
        }
        logging.info("llm_stream_response: Final payload prepared successfully")
    except Exception as e:
        logging.error(f"llm_stream_response: Error during mapping or payload creation: {e}")
        final = {"symptoms": accu, "error_message": str(e)}
        logging.error(traceback.format_exc())

    yield _create_sse_data_string("final", "llama3.2:1b", delta_content=json.dumps(final), finish_reason="stop")
    logging.info("llm_stream_response: Sending final_metadata and [DONE]")
    yield f"data: {json.dumps({'type': 'final_metadata', 'accumulated_symptoms': accu})}\n\n"
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
    :return: A StreamingResponse object is being returned with the llm_stream_response function and
    the ICD-10 data. The media type is set to "text/event-stream".
    """
    messages = chat_request.messages
    icd10 = request.app.state.icd10

    if not messages:
        raise HTTPException(
            status_code=400, detail="Missing 'messages' field in request body."
        )

    return StreamingResponse(
        llm_stream_response(chat_request, icd10),
        media_type="text/event-stream",
    )
