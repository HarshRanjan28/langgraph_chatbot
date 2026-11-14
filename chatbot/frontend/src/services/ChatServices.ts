
import type {
    ChatRequest,
    ChatResponse,
    ChatMessageHistoryResponse
} from "../types/Chattypes";

export const API = "http://localhost:8000";

// Normal API request
export async function sendMessge(
    thread_id: string,
    message: string
): Promise<ChatResponse> {

    const body: ChatRequest = { message };

    const response = await fetch(
        `${API}/chat/${thread_id}`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(body)
        }
    );

    if (!response.ok) {
        throw new Error("Failed to send message");
    }

    return response.json();
}


// Load conversation history
export async function loadConversation(
    thread_id: string
): Promise<ChatMessageHistoryResponse> {

    const response = await fetch(
        `${API}/chat/${thread_id}`
    );

    if (!response.ok) {
        throw new Error("Failed to load conversation");
    }

    return response.json();
}


// Streaming API request
export async function streamMessage(
    thread_id: string,
    message: string,
    onChunk: (content: string) => void
): Promise<void> {

    const body: ChatRequest = { message };

    const response = await fetch(
        `${API}/chat/${thread_id}`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(body)
        }
    );

    if (!response.ok) {
        throw new Error("Failed to stream message");
    }

    if (!response.body) {
        throw new Error("Response body is empty");
    }

    const reader = response.body.getReader();

    const decoder = new TextDecoder();

    let buffer = "";

    while (true) {

        const { value, done } = await reader.read();

        if (done) break;

        buffer += decoder.decode(value, {
            stream: true
        });

        const events = buffer.split("\n\n");

        buffer = events.pop() || "";

        for (const event of events) {

            const line = event
                .split("\n")
                .find(line => line.startsWith("data:"));

            if (!line) continue;

            const data = line.slice(5).trim();

            if (data === "[DONE]") {
                return;
            }

            try {

                const parsed = JSON.parse(data);

                if (parsed.error) {
                    throw new Error(parsed.error);
                }

                if (typeof parsed.content === "string") {
                    onChunk(parsed.content);
                }

            } catch (error) {

                if (error instanceof SyntaxError) {
                    console.error("Invalid SSE JSON:", data);
                    continue;
                }

                throw error;
            }
        }
    }

    // Process remaining buffered event
    buffer += decoder.decode();

    if (buffer.trim()) {

        const line = buffer
            .split("\n")
            .find(line => line.startsWith("data:"));

        if (line) {

            const data = line.slice(5).trim();

            if (data !== "[DONE]") {

                const parsed = JSON.parse(data);

                if (parsed.error) {
                    throw new Error(parsed.error);
                }

                if (typeof parsed.content === "string") {
                    onChunk(parsed.content);
                }
            }
        }
    }
}

// Upload PDF and index it in FAISS
export const uploadPDF = async (
  threadId: string,
  file: File
) => {
  const formData = new FormData();

  formData.append("thread_id", threadId);
  formData.append("file", file);

  const response = await fetch(`${API}/upload-pdf`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(error || "PDF upload failed");
  }

  return response.json();
};

// Get uploaded document information for a thread
export const getThreadDocument = async (threadId: string) => {
  const response = await fetch(
    `${API}/document/${threadId}`
  );

  if (response.status === 404) {
    return null;
  }

  if (!response.ok) {
    throw new Error("Could not fetch document information");
  }

  return response.json();
};
