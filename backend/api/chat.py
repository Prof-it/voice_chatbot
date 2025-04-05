from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI
import os
import asyncio
from dotenv import load_dotenv
import logging
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json
from utils.preprocess import preprocess_text
from utils.predict import predict_diseases
from utils.drug import search_drug_info
import numpy as np
import traceback
load_dotenv()

logging.basicConfig(level=logging.DEBUG)  # Debug logging enabled

# Load OpenAI API Key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("Missing OpenAI API key in environment variables.")

# Initialize OpenAI Client (Async)
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# FastAPI Router
chat_router = APIRouter()

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    accumulated_symptoms: Optional[List[str]] = []


SYSTEM_PROMPT = {
    "role": "system",
    "content": """
    You are a medical assistant integrated with function tooling. Your task is to extract all clearly mentioned symptoms from the user's message, regardless of the body region or condition.

    Extraction Rules:
    - Only extract clearly stated symptoms or complaints of illness. Do not infer or assume symptoms that are not explicitly mentioned.
    - Return symptoms exactly as stated by the user, e.g., "ear pain", "fever", "difficulty sleeping".
    - If no explicit symptoms are present, return an empty list [].
    - Do NOT include greetings (e.g., "Hi", "Hello"), general well-being statements (e.g., "I feel bad"), or unrelated phrases as symptoms.
    - Provide symptoms as a JSON list of strings, no explanations or extra content.

    Example outputs:
    - User: "Hi, I have a sore throat and nasal congestion" → Symptoms: ["sore throat", "nasal congestion"]
    - User: "My daughter is vomiting and has high fever" → Symptoms: ["vomiting", "fever"]
    - User: "Hey!" → Symptoms: []
    - User: "I feel terrible" → Symptoms: []
    """
}

# Function Tool Definition
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "extract_top_symptoms",
            "description": "Extracts the top 3 ENT-related symptoms explicitly mentioned by the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symptoms": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "description": "A clearly identified ENT-related symptom."
                        },
                        "description": "List of clearly identified ENT-related symptoms."
                    }
                },
                "required": ["symptoms"]
            }
        }
    }
]

async def openai_stream_response(chat_request, medical_advice_data):
    """
    Async generator that streams responses from OpenAI and processes function tool calls.
    """
    try:
        messages = chat_request.messages
        accumulated_symptoms = chat_request.accumulated_symptoms

        # logging.debug(f"Received messages: {messages}")
        logging.debug(f"Accumulated symptoms: {accumulated_symptoms}")

        # ✅ Ensure messages are formatted correctly
        tool_choice = "auto" if len(messages) < 2 else {"type": "function", "function": {"name": "extract_top_symptoms"}}
        response = await client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[SYSTEM_PROMPT, *messages],
            stream=True,
            tools=TOOLS,
            tool_choice={"type": "function", "function": {"name": "extract_top_symptoms"}},
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
                        final_tool_calls[index] = {"name": tool_call.function.name, "arguments": ""}
                    
                    # ✅ Accumulate arguments as they come in chunks
                    if tool_call.function and tool_call.function.arguments:
                        final_tool_calls[index]["arguments"] += tool_call.function.arguments

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
                        "delta": {
                            "content": content if content else None
                        },
                        "finish_reason": choices[0].finish_reason
                    }
                ]
            }

            yield f"data: {json.dumps(response_data)}\n\n"

        logging.debug(f"Final tool calls: {final_tool_calls}")

        # ✅ Process function calls after fully receiving arguments
        for index, tool_call in final_tool_calls.items():
            if tool_call["name"] == "extract_top_symptoms":
                try:
                    logging.debug(f"Processing tool call: {tool_call}")
                    extracted_args = json.loads(tool_call["arguments"])  # ✅ Ensure proper JSON parsing                    
                    symptoms_list = extracted_args.get("symptoms", [])
                    new_symptoms = [symptom for symptom in symptoms_list if symptom not in accumulated_symptoms]
                    accumulated_symptoms.extend(new_symptoms)
                    accumulated_symptoms = list(set(accumulated_symptoms))  # Remove duplicates

                    logging.debug(f"Extracted Symptoms: {symptoms_list}")
                    if not accumulated_symptoms:
                        content_string = (
                            "Hello! If you have any symptoms related to ear, nose, or throat concerns, "
                            "please let me know so I can assist you further."
                        )
                    elif len(accumulated_symptoms) < 3:
                        content_string = (
                            f"I understand you're experiencing: {', '.join(accumulated_symptoms)}. "
                            "Could you please tell me if you're experiencing additional symptoms?"
                        )
                    else:    
                        cleaned_symptoms = preprocess_text(accumulated_symptoms)
                        predicted_disease = predict_diseases(cleaned_symptoms)

                        logging.debug(f"Predicted Disease: {predicted_disease} type: {type(predicted_disease)}")                        

                        drug_info = search_drug_info(predicted_disease, medical_advice_data, cleaned_symptoms)

                        if not drug_info:
                            drug_info = {
                                "error": "No specific medications found for this condition."
                            }

                        # Ensure the disease name is formatted correctly
                        if isinstance(predicted_disease, np.ndarray):  # If it's a NumPy array, extract the first element
                            predicted_disease = predicted_disease[0]

                        if not isinstance(predicted_disease, str):  # Final check to ensure it's a string
                            predicted_disease = str(predicted_disease)

                        predicted_disease = predicted_disease.strip().title()

                        content_string = {
                            "symptoms": accumulated_symptoms,
                            "disease": predicted_disease,                            
                            "drugs": drug_info
                        }
                        logging.debug(f"Drug Info: {drug_info}")

                    function_response_data = {
                        "id": f"tool-call-{index}",
                        "object": "function_result",
                        "created": int(asyncio.get_event_loop().time()),
                        "model": "gpt-4-turbo",
                        "system_fingerprint": "function_call",
                        "choices": [
                            {
                                "index": index,
                                "delta": {
                                    "content": content_string
                                },
                                "finish_reason": "stop"
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
    Endpoint for streaming OpenAI chat responses with function tooling.
    """
    
    messages = chat_request.messages
    medical_advice_data = request.app.state.medical_advice_data

    if not messages:
        raise HTTPException(status_code=400, detail="Missing 'messages' field in request body.")

    return StreamingResponse(openai_stream_response(chat_request, medical_advice_data), media_type="text/event-stream")

def generate_advice(disease: str) -> str:
    """
    Generates medical advice based on predicted disease.
    """
    advice_map = {
        "Common Cold": "Stay hydrated, rest, and take over-the-counter cold medications.",
        "Flu": "Drink plenty of fluids, rest, and consult a doctor if symptoms persist.",
        "Otitis Media": "If ear pain persists, consult an ENT specialist immediately.",
        "Allergic Rhinitis": "Avoid allergens, use antihistamines, and keep indoor air clean."
    }
    return advice_map.get(disease, "Consult a doctor for an accurate diagnosis and treatment plan.")
