import { useState, useRef, useEffect } from "react";
import Message from "./Message";
import Loader from "./Loader";
import { StructuredContent } from "./StructuredMessageContent";


const BACKEND_URL = process.env.VITE_API_URL || "http://voice-backend:8000";
const API_URL = `${BACKEND_URL}/chat`;
const TRANSCRIBE_URL = `${BACKEND_URL}/transcribe`;
const MAX_MESSAGES = 20;

const Chat = () => {
    const accumulatedSymptomsRef = useRef<string[]>([]);
    const [messages, setMessages] = useState<{ role: string; content: string | StructuredContent }[]>([]);
    const [userInput, setUserInput] = useState("");
    const [loading, setLoading] = useState(false);
    const [chatLimitReached, setChatLimitReached] = useState(false);
    const [transcribing, setTranscribing] = useState(false);
    const [recording, setRecording] = useState(false);
    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const audioChunksRef = useRef<Blob[]>([]);

    const sendMessage = async () => {
        if (!userInput.trim() || chatLimitReached) return;
    
        const userMessage = { role: "user", content: userInput };
        let updatedMessages = [...messages, userMessage];
    
        if (updatedMessages.length > MAX_MESSAGES) {
            updatedMessages = updatedMessages.slice(-MAX_MESSAGES);
            setChatLimitReached(true);
        }
    
        setMessages(updatedMessages);
        setUserInput("");
        setLoading(true);
    
        try {
            const response = await fetch(API_URL, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    messages: updatedMessages,
                    accumulated_symptoms: accumulatedSymptomsRef.current,
                }),
            });
    
            if (!response.body) throw new Error("No response body from server.");
    
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let newContent = "";
    
            let botMessage = { role: "assistant", content: "" };
            setMessages((prev) => [...prev, botMessage]);
    
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
    
                const chunk = decoder.decode(value, { stream: true });
    
                chunk.split("\n").forEach((line) => {
                    if (!line.startsWith("data: ")) return;
                    const data = line.replace("data: ", "").trim();
                    if (data === "[DONE]") return;
    
                    try {
                        const parsed = JSON.parse(data);
    
                        // Update symptom state if present
                        if (parsed.accumulated_symptoms) {
                            accumulatedSymptomsRef.current = parsed.accumulated_symptoms;
                            return;
                        }
    
                        const delta = parsed?.choices?.[0]?.delta;
                        if (delta?.content !== undefined && delta.content !== null) {
                            let content = delta.content;
    
                            // Attempt to parse structured JSON (e.g., symptoms)
                            let structured: StructuredContent | null = null;

                            if (typeof content === "string") {
                                try {
                                    const maybeObj = JSON.parse(content);
                                    if (
                                        typeof maybeObj === "object" &&
                                        (maybeObj.symptoms || maybeObj.mappings || maybeObj.icd10 || maybeObj.appointment)
                                    ) {
                                        structured = maybeObj;
                                    }
                                } catch {
                                    // not a JSON string — treat as plain markdown
                                }
                            }
    
                            if (structured) {
                                setMessages((prevMessages) => {
                                    const updated = [...prevMessages];
                                    updated[updated.length - 1].content = structured!;
                                    return updated.length > MAX_MESSAGES ? updated.slice(-MAX_MESSAGES) : updated;
                                });
                            }
                             else {
                                newContent += typeof content === "string" ? content : "";
                                setMessages((prevMessages) => {
                                    const updated = [...prevMessages];
                                    updated[updated.length - 1].content = newContent;
                                    return updated.length > MAX_MESSAGES ? updated.slice(-MAX_MESSAGES) : updated;
                                });
                            }
                        }
                    } catch (error) {
                        console.error("Error parsing chunk:", error);
                    }
                });
            }
        } catch (error) {
            console.error("Streaming error:", error);
            setMessages((prev) => [...prev, { role: "assistant", content: "Error fetching response." }]);
        } finally {
            setLoading(false);
        }
    };
    

    const startRecording = async () => {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const mediaRecorder = new MediaRecorder(stream);
        mediaRecorderRef.current = mediaRecorder;
        audioChunksRef.current = [];

        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                audioChunksRef.current.push(event.data);
            }
        };

        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
            const formData = new FormData();
            formData.append("file", audioBlob, "recording.webm");

            setTranscribing(true);

            try {
                const response = await fetch(TRANSCRIBE_URL, {
                    method: "POST",
                    body: formData,
                });

                const data = await response.json();
                setUserInput(data.text || ""); // Autofill the input box with transcript
            } catch (err) {
                console.error("Transcription failed", err);
            }
            finally {
                setTranscribing(false);
            }
        };

        mediaRecorder.start();
        setRecording(true);
    };

    const stopRecording = () => {
        mediaRecorderRef.current?.stop();
        setRecording(false);
    };

    const cancelRecording = () => {
        if (mediaRecorderRef.current?.state === "recording") {
            mediaRecorderRef.current.ondataavailable = null; // prevent data from being stored
            mediaRecorderRef.current.onstop = null; // prevent transcription trigger
            mediaRecorderRef.current.stop();
        }
        setRecording(false);
    };

    return (
        <div className="flex flex-col h-screen bg-gray-100 dark:bg-gray-900 p-4">
            <div className="flex-grow overflow-y-auto p-2 space-y-2">
                {messages.map((msg, index) => (
                    <Message key={index} role={msg.role} content={msg.content} />
                ))}
                {loading && <Loader />}
                {transcribing && (
                    <div className="text-blue-500 text-center p-2">
                        Transcribing voice message...
                    </div>
                )}
            </div>

            {chatLimitReached && (
                <div className="text-red-500 text-center p-2">
                    Chat limit reached. Please refresh the chat to start a new conversation.
                </div>
            )}

            <div className="flex p-2 border-t bg-white dark:bg-gray-800">
                <input
                    type="text"
                    className="flex-grow p-2 border rounded-lg dark:text-white dark:bg-gray-700"
                    value={userInput}
                    onChange={(e) => setUserInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && sendMessage()}
                    placeholder={chatLimitReached ? "Chat limit reached..." : "Ask a medical question..."}
                    disabled={chatLimitReached}
                />
                {/* <button
                    onClick={recording ? stopRecording : startRecording}
                    className={`ml-2 px-4 py-2 rounded-lg ${recording ? "bg-red-500" : "bg-green-500"} text-white`}
                    disabled={loading || chatLimitReached}
                >
                    {recording ? "Stop" : "🎤"}
                </button> */}
                {recording ? (
                    <>
                        <button
                            onClick={stopRecording}
                            className="ml-2 px-4 py-2 rounded-lg bg-red-500 text-white"
                            disabled={loading || chatLimitReached}
                        >
                            Stop
                        </button>
                        <button
                            onClick={cancelRecording}
                            className="ml-2 px-4 py-2 rounded-lg bg-gray-400 text-white hover:bg-gray-500"
                            disabled={loading || chatLimitReached}
                        >
                            ❌ Cancel
                        </button>
                    </>
                ) : (
                    <button
                        onClick={startRecording}
                        className="ml-2 px-4 py-2 rounded-lg bg-green-500 text-white"
                        disabled={loading || chatLimitReached}
                    >
                        🎤
                    </button>
                )}

                <button
                    className="ml-2 bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600"
                    onClick={sendMessage}
                    disabled={loading || chatLimitReached || transcribing}
                >
                    Send
                </button>
            </div>
        </div>
    );
};

export default Chat;
