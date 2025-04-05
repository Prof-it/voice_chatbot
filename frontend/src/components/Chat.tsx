import { useState, useRef } from "react";
import Message from "./Message";
import Loader from "./Loader";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000"; // Update if hosted
const API_URL = `${BACKEND_URL}/chat`; // Update if hosted
const MAX_MESSAGES = 20; // ✅ Chat limit

const Chat = () => {
    const accumulatedSymptomsRef = useRef<string[]>([]);
    const [messages, setMessages] = useState<{ role: string; content: string }[]>([]);
    const [userInput, setUserInput] = useState("");
    const [loading, setLoading] = useState(false);
    const [chatLimitReached, setChatLimitReached] = useState(false); // ✅ Track if chat limit is reached

    const sendMessage = async () => {
        if (!userInput.trim() || chatLimitReached) return; // ✅ Prevent sending if limit is reached

        const userMessage = { role: "user", content: userInput };
        let updatedMessages = [...messages, userMessage];

        // ✅ Enforce chat history limit (Keep only last 20 messages)
        if (updatedMessages.length > MAX_MESSAGES) {
            updatedMessages = updatedMessages.slice(-MAX_MESSAGES);
            setChatLimitReached(true); // ✅ Stop further messages
        }

        setMessages(updatedMessages);
        setUserInput("");
        setLoading(true);

        try {
            const response = await fetch(API_URL, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ messages: updatedMessages, accumulated_symptoms: accumulatedSymptomsRef.current }), // ✅ Send full chat history (last 20 messages)
            });

            if (!response.body) {
                throw new Error("No response body from server.");
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let newContent = "";
            let toolCallArgs = ""; // Store tool call argument construction

            let botMessage = { role: "assistant", content: "" };
            setMessages((prev) => [...prev, botMessage]); // ✅ Add an empty bot message

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });

                chunk.split("\n").forEach((line) => {
                    if (line.startsWith("data: ")) {
                        const data = line.replace("data: ", "").trim();
                        if (data === "[DONE]") return;

                        try {
                            const parsed = JSON.parse(data);

                            console.log("Parsed data:", parsed);

                            if (parsed.accumulated_symptoms) {
                                accumulatedSymptomsRef.current = parsed.accumulated_symptoms;
                            }

                            // 🔹 Handle assistant messages (streamed or structured)
                            const delta = parsed?.choices?.[0]?.delta;

                            if (delta && delta.content !== undefined && delta.content !== null) {
                                const content = delta.content;

                                // 🧠 Handle streamed string content (typical for LLMs)
                                if (typeof content === "string") {
                                    newContent += content;

                                    setMessages((prevMessages) => {
                                        const updated = [...prevMessages];
                                        updated[updated.length - 1].content = newContent;
                                        return updated.length > MAX_MESSAGES
                                            ? updated.slice(-MAX_MESSAGES)
                                            : updated;
                                    });
                                }

                                // 📦 Handle complete structured object (symptoms, disease, drugs, etc.)
                                else if (typeof content === "object") {
                                    console.log("📦 Received structured assistant response:", content);

                                    setMessages((prevMessages) => {
                                        const updated = [...prevMessages];
                                        updated[updated.length - 1].content = content;
                                        return updated.length > MAX_MESSAGES
                                            ? updated.slice(-MAX_MESSAGES)
                                            : updated;
                                    });
                                }
                            }


                            // 🔹 Handle tool calls (function calls)
                            if (parsed.tool_calls) {
                                console.log("Tool calls:", parsed.tool_calls);
                                parsed.tool_calls.forEach((toolCall: any) => {
                                    if (toolCall.function?.arguments) {
                                        toolCallArgs += toolCall.function.arguments;
                                    }
                                });

                                setMessages((prev) => {
                                    const updatedMessages = [...prev];
                                    updatedMessages[updatedMessages.length - 1].content = `Processing: ${toolCallArgs}`;
                                    return updatedMessages.length > MAX_MESSAGES ? updatedMessages.slice(-MAX_MESSAGES) : updatedMessages;
                                });
                            }

                            // 🔹 Handle final tool response (like extracted diseases)
                            // if (parsed.toolResponse) {
                            //     setMessages((prev) => {
                            //         let updatedMessages = [...prev, { role: "assistant", content: parsed.toolResponse }];
                            //         return updatedMessages.length > MAX_MESSAGES ? updatedMessages.slice(-MAX_MESSAGES) : updatedMessages;
                            //     });
                            // }
                            // console.log("Tool response:", parsed.toolResponse);
                            if (parsed.toolResponse) {
                                console.log("Tool response:", parsed.toolResponse);
                                setMessages((prev) => {
                                    const newMessage = {
                                        role: "assistant",
                                        content: parsed.toolResponse, // this will be an object now
                                    };
                                    return [...prev, newMessage].slice(-MAX_MESSAGES);
                                });
                            }

                        } catch (error) {
                            console.error("Error parsing JSON:", error);
                        }
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


    return (
        <div className="flex flex-col h-screen bg-gray-100 dark:bg-gray-900 p-4">
            <div className="flex-grow overflow-y-auto p-2 space-y-2">
                {messages.map((msg, index) => {
                    return <Message key={index} role={msg.role} content={msg.content} />;
                })}
                {loading && <Loader />}
            </div>

            {/* ✅ Show chat limit reached message */}
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
                    disabled={chatLimitReached} // ✅ Disable input when limit is reached
                />
                <button
                    className="ml-2 bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600"
                    onClick={sendMessage}
                    disabled={loading || chatLimitReached} // ✅ Disable send button when limit is reached
                >
                    Send
                </button>
            </div>
        </div>
    );
};

export default Chat;
