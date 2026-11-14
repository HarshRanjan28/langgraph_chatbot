import React, { useState, useEffect, useRef } from "react";

import {
  loadConversation,
  streamMessage,
  uploadPDF,
  getThreadDocument,
} from "./services/ChatServices";

interface Message {
  role: "user" | "ai";
  content: string;
}

interface DocumentInfo {
  filename: string;
  documents: number;
  chunks: number;
}

const App: React.FC = () => {
  // Chat states
  const [threadId, setThreadId] = useState<string>(() => crypto.randomUUID());

  const [chatThreads, setChatThreads] = useState<string[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");

  const [loading, setLoading] = useState(false);

  // RAG states
  const [document, setDocument] = useState<DocumentInfo | null>(null);

  const [uploading, setUploading] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Initial conversation
  useEffect(() => {
    handleLoadConversation(threadId);
  }, []);

  // Add thread
  const addThread = (id: string) => {
    setChatThreads((prev) => (prev.includes(id) ? prev : [...prev, id]));
  };

  // New chat
  const newChat = () => {
    const newThreadId = crypto.randomUUID();

    setThreadId(newThreadId);
    setMessages([]);
    setDocument(null);
    setInput("");

    addThread(newThreadId);
  };

  // Load conversation
  const handleLoadConversation = async (id: string) => {
    setThreadId(id);
    setMessages([]);
    setDocument(null);

    try {
      const data = await loadConversation(id);

      setMessages(data.messages || []);

      // Load PDF information for this thread
      const doc = await getThreadDocument(id);

      setDocument(doc);
    } catch (error) {
      console.error("Loading conversation error:", error);
    }
  };

  // Upload PDF
  const handlePDFUpload = async (
    event: React.ChangeEvent<HTMLInputElement>,
  ) => {
    const file = event.target.files?.[0];

    if (!file) return;

    // Only PDF files
    if (file.type !== "application/pdf") {
      alert("Please upload a PDF file.");
      event.target.value = "";
      return;
    }

    setUploading(true);

    try {
      const result = await uploadPDF(threadId, file);

      setDocument({
        filename: result.filename,
        documents: result.documents,
        chunks: result.chunks,
      });

      addThread(threadId);

      alert("PDF uploaded and indexed successfully!");
    } catch (error) {
      console.error("PDF upload error:", error);
      alert("Failed to upload PDF. Please try again.");
    } finally {
      setUploading(false);

      // Allow selecting the same PDF again
      event.target.value = "";
    }
  };

  // Send message
  const handleSendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMessage = input;

    setInput("");
    setLoading(true);

    setMessages((prev) => [
      ...prev,
      {
        role: "user",
        content: userMessage,
      },
      {
        role: "ai",
        content: "",
      },
    ]);

    addThread(threadId);

    try {
      await streamMessage(threadId, userMessage, (chunk: string) => {
        setMessages((prev) => {
          const updated = [...prev];

          const lastIndex = updated.length - 1;

          updated[lastIndex] = {
            ...updated[lastIndex],
            content: updated[lastIndex].content + chunk,
          };

          return updated;
        });
      });
    } catch (error) {
      console.error("Streaming error:", error);

      setMessages((prev) => {
        const updated = [...prev];

        const lastIndex = updated.length - 1;

        if (updated[lastIndex]?.role === "ai") {
          updated[lastIndex] = {
            ...updated[lastIndex],
            content:
              updated[lastIndex].content ||
              "Something went wrong. Please try again.",
          };
        }

        return updated;
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        display: "flex",
        height: "100vh",
        fontFamily: "Arial",
      }}
    >
      {/* Sidebar */}

      <div
        style={{
          width: "250px",
          background: "#202123",
          color: "white",
          padding: "20px",
        }}
      >
        <h2>LangGraph Chatbot</h2>

        <button onClick={newChat}>+ New Chat</button>

        <h3>My Conversations</h3>

        {chatThreads
          .slice()
          .reverse()
          .map((id) => (
            <button
              key={id}
              onClick={() => handleLoadConversation(id)}
              style={{
                display: "block",
                width: "100%",
                margin: "8px 0",
                padding: "10px",
                background: threadId === id ? "#444" : "#303030",
                color: "white",
                border: "none",
                cursor: "pointer",
                overflow: "hidden",
              }}
            >
              {id.slice(0, 8)}
            </button>
          ))}
      </div>

      {/* Main Chat Area */}

      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          padding: "20px",
        }}
      >
        {/* Header */}

        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            borderBottom: "1px solid #ddd",
            paddingBottom: "15px",
          }}
        >
          <h2>Chat Assistant</h2>

          {/* PDF Upload */}

          <div>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,application/pdf"
              onChange={handlePDFUpload}
              style={{ display: "none" }}
            />

            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading || loading}
              style={{
                padding: "10px 16px",
                background: "#2563eb",
                color: "white",
                border: "none",
                borderRadius: "6px",
                cursor: "pointer",
              }}
            >
              {uploading ? "Uploading PDF..." : "📎 Upload PDF"}
            </button>
          </div>
        </div>

        {/* Uploaded Document Information */}

        {document && (
          <div
            style={{
              marginTop: "15px",
              padding: "12px",
              background: "#e8f5e9",
              border: "1px solid #a5d6a7",
              borderRadius: "8px",
              display: "flex",
              alignItems: "center",
              gap: "12px",
            }}
          >
            <span style={{ fontSize: "28px" }}>📄</span>

            <div>
              <strong>{document.filename}</strong>

              <p style={{ margin: "5px 0", fontSize: "13px" }}>
                {document.documents} documents indexed
                {" | "}
                {document.chunks} text chunks created
              </p>

              <small style={{ color: "green" }}>Ready for questions</small>
            </div>
          </div>
        )}

        {/* Messages */}

        <div
          style={{
            flex: 1,
            overflowY: "auto",
            marginTop: "15px",
          }}
        >
          {messages.map((message, index) => (
            <div
              key={index}
              style={{
                padding: "12px",
                margin: "10px",
                background: message.role === "user" ? "#dceeff" : "#eeeeee",
                borderRadius: "8px",
              }}
            >
              <strong>{message.role === "user" ? "You" : "AI"}</strong>

              <p style={{ whiteSpace: "pre-wrap" }}>
                {message.content ||
                  (loading && message.role === "ai" ? "Thinking..." : "")}
              </p>
            </div>
          ))}
        </div>

        {/* Input Area */}

        <div
          style={{
            display: "flex",
            gap: "10px",
          }}
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSendMessage();
              }
            }}
            placeholder={
              document
                ? "Ask a question about your PDF..."
                : "Type your message..."
            }
            style={{
              flex: 1,
              padding: "12px",
            }}
            disabled={loading || uploading}
          />

          <button
            onClick={handleSendMessage}
            disabled={loading || uploading || !input.trim()}
          >
            {loading ? "Thinking..." : "Send"}
          </button>
        </div>
      </div>
    </div>
  );
};

export default App;
