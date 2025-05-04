import os
import traceback
import asyncio
import logging
import json
import traceback

from utils.predict import predict_icd10, map_icd10_to_specialties
from utils.prompts import MAP_PROMPT, SYSTEM_PROMPT, TOOLS
from utils.types import ChatRequest


from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion
from dotenv import load_dotenv

from faster_whisper import WhisperModel


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
chat_router = APIRouter()

async def openai_stream_response(chat_request, icd10):
    """
    The function `openai_stream_response` processes chat messages, extracts symptoms, maps them to
    diagnoses, predicts ICD-10 codes, and suggests specialties for medical appointments.
    
    :param chat_request: The `chat_request` parameter seems to contain information related to a chat
    conversation, including messages exchanged and accumulated symptoms. The function
    `openai_stream_response` appears to interact with the OpenAI API to process these messages and
    symptoms, generating responses based on the received data
    :param icd10: The `icd10` parameter in the `openai_stream_response` function seems to be a
    dictionary containing information related to ICD-10 coding. It likely includes the following
    key-value pairs:
    """

    try:
        messages = chat_request.messages
        accumulated_symptoms = chat_request.accumulated_symptoms

        logging.debug(f"Accumulated symptoms: {accumulated_symptoms}")

        # Validate messages
        response = await client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[SYSTEM_PROMPT, *messages],
            stream=True,
            tools=TOOLS,
            tool_choice={
                "type": "function",
                "function": {"name": "extract_top_symptoms"},
            },
        )

        final_tool_calls = {}

        async for chunk in response:
            logging.debug(f"Received chunk: {chunk}")

            # ✅ Safely extract choices and tool_calls
            choices = chunk.choices
            if not choices:
                continue  # ✅ Skip empty chunks

            delta = choices[0].delta
            tool_calls = getattr(delta, "tool_calls", None)

            if tool_calls:
                for tool_call in tool_calls:
                    index = tool_call.index
                    if index not in final_tool_calls:
                        final_tool_calls[index] = {
                            "name": tool_call.function.name,
                            "arguments": "",
                        }

                    # ✅ Accumulate arguments as they come in chunks
                    if tool_call.function and tool_call.function.arguments:
                        final_tool_calls[index][
                            "arguments"
                        ] += tool_call.function.arguments

            content = getattr(delta, "content", None)

            # ✅ Maintain the expected response format
            response_data = {
                "id": chunk.id,
                "object": chunk.object,
                "created": chunk.created,
                "model": chunk.model,
                "system_fingerprint": chunk.system_fingerprint,
                "choices": [
                    {
                        "index": choices[0].index,
                        "delta": {"content": content if content else None},
                        "finish_reason": choices[0].finish_reason,
                    }
                ],
            }

            yield f"data: {json.dumps(response_data)}\n\n"

        logging.debug(f"Final tool calls: {final_tool_calls}")

        # ✅ Process function calls after fully receiving arguments
        for index, tool_call in final_tool_calls.items():
            if tool_call["name"] == "extract_top_symptoms":
                try:
                    logging.debug(f"Processing tool call: {tool_call}")
                    extracted_args = json.loads(
                        tool_call["arguments"]
                    )  # ✅ Ensure proper JSON parsing
                    symptoms_list = extracted_args.get("symptoms", [])
                    new_symptoms = [
                        symptom
                        for symptom in symptoms_list
                        if symptom not in accumulated_symptoms
                    ]
                    accumulated_symptoms.extend(new_symptoms)
                    accumulated_symptoms = list(
                        set(accumulated_symptoms)
                    )  # Remove duplicates

                    logging.debug(f"Extracted Symptoms: {symptoms_list}")
                    if not accumulated_symptoms:
                        content_string = (
                            "Hello! If you have any symptoms or health concerns, "
                            "please let me know so I can assist you further."
                        )
                    elif len(accumulated_symptoms) < 3:
                        content_string = (
                            f"I understand you're experiencing: {', '.join(accumulated_symptoms)}. "
                            "Could you please tell me about any other symptoms you might have?"
                        )
                    else:                        
                        # Map symptoms to detailed clinical diagnosis phrases
                        response: ChatCompletion = await client.chat.completions.create(
                            model="gpt-4-turbo",
                            messages=[
                                MAP_PROMPT,
                                {
                                    "role": "user",
                                    "content": json.dumps(
                                        {"symptoms": accumulated_symptoms}
                                    ),
                                },
                            ],
                            stream=False,
                            tools=TOOLS,
                            tool_choice={
                                "type": "function",
                                "function": {"name": "map_symptoms_to_diagnoses"},
                            },
                        )
                        print(f"Response: {response.choices[0]}")
                        resp_choice = response.choices[0]

                        print(f"Response choice: {resp_choice}")

                        # 1) Try the standard function_call API first
                        if resp_choice.message and resp_choice.message.function_call:
                            args_str = resp_choice.message.function_call.arguments

                        # 2) Fallback to the tool_calls list if function_call is None
                        elif resp_choice.message.tool_calls:
                            # take the last tool_call for our mapping function
                            tc = [
                                tc for tc in resp_choice.message.tool_calls
                                if tc.function.name == "map_symptoms_to_diagnoses"
                            ]
                            if not tc:
                                raise ValueError("No map_symptoms_to_diagnoses tool_call found")
                            args_str = tc[-1].function.arguments

                        else:
                            raise ValueError("No function_call or tool_calls found in response")

    
                        payload = json.loads(args_str)
                        mappings = payload.get("mappings", [])

                        print(f"Mappings: {mappings}")

                        # 4) Extract diagnosis phrases
                        detailed_diagnoses = [m["diagnosis"] for m in mappings]

                        # Use the detailed diagnosis phrases for ICD-10 mapping
                        # predict icd10 codes for the symptoms
                        icd_model = icd10["model"]
                        icd_tokenizer = icd10["tokenizer"]
                        device = icd10["device"]

                        icd_10_mappings = predict_icd10(
                            detailed_diagnoses, icd_tokenizer, icd_model, device
                        )
                        icd_codes = [item["icd10"] for item in icd_10_mappings]
                        # Map ICD-10 codes to specialties
                        specialty = map_icd10_to_specialties(icd_codes)

                        appointment = {
                            "specialty": specialty,
                            "suggestedDate": "yet to implement",
                            "suggestedTime": "yet to implement",
                        }


                        content_string = {
                            "symptoms": accumulated_symptoms,
                            "mappings": mappings,
                            "detailed_diagnoses": detailed_diagnoses,
                            "icd10": icd_10_mappings,
                            "appointment": appointment,
                            "disease": "",
                            "drugs": [],
                        }

                    function_response_data = {
                        "id": f"tool-call-{index}",
                        "object": "function_result",
                        "created": int(asyncio.get_event_loop().time()),
                        "model": "gpt-4-turbo",
                        "system_fingerprint": "function_call",
                        "choices": [
                            {
                                "index": index,
                                "delta": {"content": content_string},
                                "finish_reason": "stop",
                            }
                        ],
                        "accumulated_symptoms": accumulated_symptoms,
                    }

                    yield f"data: {json.dumps(function_response_data)}\n\n"

                except json.JSONDecodeError as e:
                    logging.error(f"JSON Decode Error: {e}")
                    yield f"data: {{'error': 'Invalid function response format'}}\n\n"

        yield "data: [DONE]\n\n"

    except Exception as e:
        # Log the error with traceback
        logging.error(traceback.format_exc())
        logging.error(f"OpenAI API Error: {e}")
        yield f"data: {{'error': 'Error fetching response from OpenAI'}}\n\n"


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
