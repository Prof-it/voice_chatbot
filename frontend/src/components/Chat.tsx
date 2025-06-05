import { useRef, useState } from "react"; // Added useEffect for potential cleanup if needed
import Loader from "./Loader";
import Message from "./Message"; // Assuming Message.tsx is in the same directory
import { StructuredContent } from "./StructuredMessageContent";
import { v4 as uuidv4 } from 'uuid';


const BACKEND_URL = process.env.VITE_API_URL || "http://localhost:8000";
const API_URL = `${BACKEND_URL}/chat`;
const TRANSCRIBE_URL = `${BACKEND_URL}/transcribe_vosk`;
const MAX_MESSAGES = 20;

// Define an interface for our message data structure
export interface MessageData {
    id: string;
    role: "user" | "assistant"; // Simplified roles for this example
    content: string | StructuredContent;
    responseTimeMs?: number; // For bot messages: total time from user send to full bot response
    ttfbMs?: number; // For bot messages: Time To First Byte
    transcriptionTimeMs?: number; // For user messages: if transcribed
}

const Chat = () => {
    const accumulatedSymptomsRef = useRef<string[]>([]);
    const [messages, setMessages] = useState<MessageData[]>([]);
    const [userInput, setUserInput] = useState("");
    const [loading, setLoading] = useState(false);
    const [chatLimitReached, setChatLimitReached] = useState(false);
    const [transcribing, setTranscribing] = useState(false);
    const [recording, setRecording] = useState(false);
    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const audioChunksRef = useRef<Blob[]>([]);
    const sseBufferRef = useRef("");   // keeps partial chunks between reads


    // State to hold the transcription time of the last recorded audio
    const [lastTranscriptionTimeMs, setLastTranscriptionTimeMs] = useState<number | null>(null);

    // Helper to update metrics for the last bot message in the state
    // This targets the message currently being streamed to.
    const updateLastBotMessageWithMetrics = (metrics: { ttfbMs?: number; responseTimeMs?: number }) => {
        setMessages(prevMessages => {
            const newMessages = [...prevMessages];
            const lastMessageIndex = newMessages.length - 1;
            if (lastMessageIndex >= 0 && newMessages[lastMessageIndex].role === "assistant") {
                const currentMessage = newMessages[lastMessageIndex];
                newMessages[lastMessageIndex] = {
                    ...currentMessage,
                    ttfbMs: metrics.ttfbMs !== undefined ? metrics.ttfbMs : currentMessage.ttfbMs,
                    responseTimeMs: metrics.responseTimeMs !== undefined ? metrics.responseTimeMs : currentMessage.responseTimeMs,
                };
            }
            return newMessages;
        });
    };


    const sendMessage = async () => {
        if (!userInput.trim() || chatLimitReached) return;

        const userMessageId = uuidv4(); // Unique ID for the user message
        const userMessage: MessageData = {
            id: userMessageId,
            role: "user",
            content: userInput,
            transcriptionTimeMs: lastTranscriptionTimeMs ?? undefined,
        };
        if (lastTranscriptionTimeMs !== null) {
            setLastTranscriptionTimeMs(null); // Reset after use
        }

        let messagesWithUserContext = [...messages, userMessage].map(m => ({ ...m, id: m.id || crypto.randomUUID() }));

        if (messagesWithUserContext.length > MAX_MESSAGES) {
            messagesWithUserContext = messagesWithUserContext.slice(messagesWithUserContext.length - MAX_MESSAGES);
            if (!chatLimitReached) {
                setChatLimitReached(true);
            }
        }

        setMessages(messagesWithUserContext); // Display user message and pruned history
        setUserInput("");
        setLoading(true);

        const botMessageId = uuidv4(); // Unique ID for the bot's response
        const botMessagePlaceholder: MessageData = {
            id: botMessageId,
            role: "assistant",
            content: "",
        };
        setMessages((prev) => [...prev, botMessagePlaceholder]); // Add placeholder for bot response

        const sendMessageStartTime = performance.now();
        let requestFailed = false;
        let currentTtfb: number | undefined = undefined;

        try {
            const response = await fetch(API_URL, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    messages: messagesWithUserContext, // Send context including the latest user message
                    accumulated_symptoms: accumulatedSymptomsRef.current,
                }),
            });

            const ttfbTime = performance.now();
            currentTtfb = parseFloat((ttfbTime - sendMessageStartTime).toFixed(2));
            console.log(`Chat API TTFB: ${currentTtfb} ms`);
            updateLastBotMessageWithMetrics({ ttfbMs: currentTtfb });

            if (!response.body) {
                requestFailed = true;
                throw new Error("No response body from server.");
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { done, value } = await reader.read();
                if (done) {
                    console.log("%c[SSE] ⛔️ stream closed", "color:orange");
                    break;
                }

                // 1) accumulate raw bytes
                sseBufferRef.current += decoder.decode(value, { stream: true });

                // 2) handle complete events
                let boundary;
                while ((boundary = sseBufferRef.current.indexOf("\n\n")) !== -1) {
                    const rawEvent = sseBufferRef.current.slice(0, boundary).trim();
                    sseBufferRef.current = sseBufferRef.current.slice(boundary + 2);

                    console.log("%c[SSE] 📦 full event:", "color:teal", rawEvent);

                    if (!rawEvent.startsWith("data: ")) continue;
                    const payload = rawEvent.slice(6);
                    if (payload === "[DONE]") {
                        console.log("%c[SSE] ✅ [DONE] received", "color:green");
                        continue;
                    }

                    const deltaText =
                        JSON.parse(payload)?.choices?.[0]?.delta?.content ?? "";
                    if (!deltaText) continue;

                    console.log("%c[SSE] ✏️  delta:", "color:blue", `"${deltaText}"`);

                    // 3) IMMUTABLE update → never mutate prev state
                    setMessages(prev =>
                        prev.map((m, i) =>
                            i === prev.length - 1 && m.role === "assistant"
                                ? {
                                    ...m,
                                    content:
                                        (typeof m.content === "string" ? m.content : "") +
                                        deltaText,
                                }
                                : m
                        )
                    );

                    // 4) optional: peek at the brand-new assistant string
                    setTimeout(() => {
                        const latest = document.querySelectorAll("[data-assistant]")?.[
                            document.querySelectorAll("[data-assistant]").length - 1
                        ]?.textContent;
                        console.log("%c[DOM] 🖥️  now shows:", "color:purple", latest);
                    }, 0);
                }
            }
        } catch (error) {
            requestFailed = true;
            console.error("Streaming or API error:", error);
            const endTime = performance.now();
            const duration = parseFloat((endTime - sendMessageStartTime).toFixed(2));
            setMessages(prev => prev.map(msg =>
                msg.id === botMessageId
                    ? { ...msg, content: "Error fetching response.", responseTimeMs: duration, ttfbMs: currentTtfb }
                    : msg
            ));
        } finally {
            setLoading(false);
            const finalEndTime = performance.now();
            const totalDuration = parseFloat((finalEndTime - sendMessageStartTime).toFixed(2));
            if (!requestFailed) {
                console.log(`Chat API call successful. Total stream processing time: ${totalDuration} ms.`);
                updateLastBotMessageWithMetrics({ responseTimeMs: totalDuration }); // ttfbMs was already set
            }
            setMessages(prev => prev.map(msg =>
                (msg.id === botMessageId && msg.content === "")
                    ? { ...msg, content: "[Response ended without content]" }
                    : msg
            ));
        }
    };

    const startRecording = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const mediaRecorder = new MediaRecorder(stream);
            mediaRecorderRef.current = mediaRecorder;
            audioChunksRef.current = [];
            mediaRecorder.ondataavailable = (event) => { if (event.data.size > 0) audioChunksRef.current.push(event.data); };
            mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
                const formData = new FormData();
                formData.append("file", audioBlob, "recording.webm");
                setTranscribing(true);
                const transcribeStartTime = performance.now();
                try {
                    const response = await fetch(TRANSCRIBE_URL, { method: "POST", body: formData });
                    const data = await response.json();
                    setUserInput(data.text || "");
                    const transcribeEndTime = performance.now();
                    const duration = parseFloat((transcribeEndTime - transcribeStartTime).toFixed(2));
                    setLastTranscriptionTimeMs(duration);
                    console.log(`Transcription successful. Time taken: ${duration} ms.`);
                } catch (err) {
                    console.error("Transcription failed", err);
                    setLastTranscriptionTimeMs(null); // Clear if transcription failed
                } finally {
                    setTranscribing(false);
                }
            };
            mediaRecorder.start();
            setRecording(true);
        } catch (error) { console.error("Failed to start recording:", error); }
    };

    const stopRecording = () => {
        mediaRecorderRef.current?.stop();
        setRecording(false);
    };
    const cancelRecording = () => {
        if (mediaRecorderRef.current?.state === "recording") {
            mediaRecorderRef.current.ondataavailable = null;
            mediaRecorderRef.current.onstop = null;
            mediaRecorderRef.current.stop();
        }
        setRecording(false);
        audioChunksRef.current = [];
    };

    return (
        <div className="flex flex-col h-screen bg-gray-100 dark:bg-gray-900 p-4">
            <div className="flex-grow overflow-y-auto p-2 space-y-2">
                {messages.map((msg) => (
                    <Message
                        key={msg.id} // Use unique ID as key
                        role={msg.role}
                        content={msg.content}
                        responseTimeMs={msg.responseTimeMs}
                        ttfbMs={msg.ttfbMs}
                        transcriptionTimeMs={msg.transcriptionTimeMs}
                    />
                ))}
                {loading && <Loader />}
                {transcribing && <div className="text-blue-500 text-center p-2">Transcribing...</div>}
            </div>
            {chatLimitReached && <div className="text-red-500 text-center p-2">Chat limit reached.</div>}
            <div className="flex p-2 border-t bg-white dark:bg-gray-800">
                <input
                    type="text"
                    className="flex-grow p-2 border rounded-lg dark:text-white dark:bg-gray-700"
                    value={userInput}
                    onChange={(e) => setUserInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && sendMessage()}
                    placeholder={chatLimitReached ? "Chat limit reached..." : "Ask a medical question..."}
                    disabled={chatLimitReached || loading || transcribing}
                />
                {recording ? (
                    <>
                        <button onClick={stopRecording} className="ml-2 px-4 py-2 rounded-lg bg-red-500 text-white" disabled={loading}>Stop</button>
                        <button onClick={cancelRecording} className="ml-2 px-4 py-2 rounded-lg bg-gray-400 text-white hover:bg-gray-500" disabled={loading}>❌ Cancel</button>
                    </>
                ) : (
                    <button onClick={startRecording} className="ml-2 px-4 py-2 rounded-lg bg-green-500 text-white" disabled={loading || chatLimitReached || transcribing}>🎤</button>
                )}
                <button className="ml-2 bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600" onClick={sendMessage} disabled={loading || chatLimitReached || transcribing || !userInput.trim()}>Send</button>
            </div>
        </div>
    );
};
export default Chat;