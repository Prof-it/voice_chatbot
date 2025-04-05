class ResponseParser {
    private toolCallArgs: Record<string, string> = {};
    private messages: { role: string; content: string }[] = [];

    constructor() {}

    /**
     * Processes a streamed response chunk.
     * @param chunk Parsed JSON chunk from server.
     */
    public parseChunk(chunk: any) {
        // 🔹 Handle regular assistant responses
        if (chunk.content) {
            this.appendMessage("bot", chunk.content);
        }

        // 🔹 Handle tool calls (accumulate arguments over multiple chunks)
        if (chunk.tool_calls) {
            chunk.tool_calls.forEach((toolCall: any) => {
                const toolId = toolCall.id;

                if (!this.toolCallArgs[toolId]) {
                    this.toolCallArgs[toolId] = "";
                }

                if (toolCall.function?.arguments) {
                    this.toolCallArgs[toolId] += toolCall.function.arguments;
                }
            });

            this.appendMessage("bot", `Processing: ${JSON.stringify(this.toolCallArgs)}`);
        }

        // 🔹 Handle tool responses (final structured result)
        if (chunk.toolResponse) {
            this.appendMessage("bot", this.formatToolResponse(chunk.toolResponse));
        }
    }

    /**
     * Formats structured tool responses.
     * @param toolResponse Tool call result.
     * @returns Formatted chatbot-friendly response.
     */
    private formatToolResponse(toolResponse: any): string {
        if (Array.isArray(toolResponse)) {
            if (toolResponse.length === 0) {
                return "I couldn't detect any relevant ENT conditions.";
            }

            if (typeof toolResponse[0] === "string") {
                // This means we got disease names
                return `Based on your symptoms, possible ENT conditions are: **${toolResponse.join(", ")}**.\n\nWould you like details on **medications, side-effects, and warnings** for these?`;
            } else {
                // This means we got structured medical advice
                let response = "**Here is the medical information based on your query:**\n\n";
                toolResponse.forEach((entry) => {
                    response += `🔹 **Disease:** ${entry.disease}\n`;
                    response += `💊 **Medication:** ${entry.medication}\n`;
                    response += `⚠️ **Side-effects:** ${entry.side_effects.join(", ")}\n\n`;
                });
                return response.trim();
            }
        }

        return "I couldn't process this request.";
    }

    /**
     * Adds a new message to the chat history.
     * @param role "user" or "bot"
     * @param content The message content.
     */
    private appendMessage(role: string, content: string) {
        if (!content) return;
        if (this.messages.length > 0 && this.messages[this.messages.length - 1].role === role) {
            this.messages[this.messages.length - 1].content += content;
        } else {
            this.messages.push({ role, content });
        }
    }

    /**
     * Returns the parsed messages.
     */
    public getMessages() {
        return this.messages;
    }
}

export default ResponseParser;
