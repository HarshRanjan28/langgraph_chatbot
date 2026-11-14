export interface Message {
    role: "user" | "ai";
    content:string
}

export interface ChatRequest {
    message:string
}

export interface ChatResponse {
    response:string
}

export interface ChatMessageHistoryResponse {
    messages: Message[] 
}