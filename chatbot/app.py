
import asyncio
import json

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI,UploadFile,File,Form,HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from fastmcp import FastMCP

from pydantic import BaseModel

from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    AIMessageChunk
)

from backend import create_chatbot,ingest_pdf,__THREAD_METADATA

# --------------------------------------------------
# REQUEST MODELS
# --------------------------------------------------

class ChatRequest(BaseModel):
    message: str


class ProductCreate(BaseModel):
    name: str
    price: float
    description: Optional[str] = None

# --------------------------------------------------
# MAIN FASTAPI APPLICATION
# --------------------------------------------------

app = FastAPI()


@app.get("/health")
def system_health_check():
    return {"status": "healthy"}


@app.post("/products")
def create_product(product: ProductCreate):

    return {
        "status": "success",
        "product": product.model_dump()
    }


# --------------------------------------------------
# FASTMCP SERVER
# --------------------------------------------------

mcp = FastMCP.from_fastapi(
    app=app,
    name="chatbot-mcp"
)


@mcp.tool
def calculate_bulk_discount(
    quantity: int,
    unit_price: float
) -> float:
    """
    Calculate wholesale cost with bulk discounts.

    Orders of 100 or more receive a 15% discount.
    """

    if quantity >= 100:
        return quantity * unit_price * 0.85

    return quantity * unit_price


@mcp.resource("store://return-policy")
def get_return_policy():
    """
    Returns the store's return policy.
    """

    return "Customers can return products within 30 days for a full refund."


# --------------------------------------------------
# MCP HTTP APPLICATION
# --------------------------------------------------

mcp_http_app = mcp.http_app(path="/")


# --------------------------------------------------
# CHATBOT INITIALIZATION
# --------------------------------------------------

chatbot = None

chatbot_lock = asyncio.Lock()


async def get_chatbot():

    global chatbot

    if chatbot is None:

        async with chatbot_lock:

            if chatbot is None:

                print("\nInitializing LangGraph chatbot...")

                chatbot = await create_chatbot()

                print("Chatbot initialized successfully!")

    return chatbot


# --------------------------------------------------
# COMBINED FASTAPI + MCP APPLICATION
# --------------------------------------------------

combined_app = FastAPI(
    lifespan=mcp_http_app.lifespan
)


# Include regular FastAPI routes
combined_app.include_router(app.router)


# Mount MCP server
combined_app.mount(
    "/mcp",
    mcp_http_app
)


# CORS
combined_app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


# --------------------------------------------------
# STREAMING CHAT ENDPOINT
# --------------------------------------------------

@combined_app.post("/chat/{thread_id}")
async def chat(thread_id: str, request: ChatRequest):

    # Initialize chatbot when first request arrives.
    agent = await get_chatbot()

    async def generate():

        config = {
            "configurable": {
                "thread_id": thread_id
            }
        }

        try:

            async for message_chunk, metadata in agent.astream(
                {
                    "messages": [
                        HumanMessage(content=request.message)
                    ]
                },
                config=config,
                stream_mode="messages"
            ):

                if isinstance(message_chunk, AIMessageChunk):

                    content = message_chunk.content

                    if isinstance(content, str) and content:

                        yield (
                            f"data: {json.dumps({'content': content})}\n\n"
                        )

            yield "data: [DONE]\n\n"

        except Exception as e:

            print("Streaming error:", str(e))

            error_data = json.dumps({
                "error": str(e)
            })

            yield f"data: {error_data}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# --------------------------------------------------
# CHAT HISTORY ENDPOINT
# --------------------------------------------------

@combined_app.get("/chat/{thread_id}")
async def get_chat_history(thread_id: str):

    agent = await get_chatbot()

    state = await agent.aget_state(
        config={
            "configurable": {
                "thread_id": thread_id
            }
        }
    )

    messages = state.values.get("messages", [])

    history = []

    for message in messages:

        if isinstance(message, HumanMessage):

            role = "user"

        elif isinstance(message, AIMessage):

            role = "ai"

        else:
            continue

        if isinstance(message.content, str):

            history.append({
                "role": role,
                "content": message.content
            })

    return {
        "messages": history
    }

# --------------------------------------------------
# PDF UPLOAD / RAG ENDPOINT
# --------------------------------------------------

@combined_app.post("/upload-pdf")
async def upload_pdf(
    thread_id: str = Form(...),
    file: UploadFile = File(...)
):

    # Validate file extension
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported"
        )

    try:

        # Read uploaded PDF
        file_bytes = await file.read()

        if not file_bytes:
            raise HTTPException(
                status_code=400,
                detail="Uploaded PDF is empty"
            )

        # Optional: enforce a 20 MB limit
        if len(file_bytes) > 20 * 1024 * 1024:
            raise HTTPException(
                status_code=413,
                detail="PDF size cannot exceed 20 MB"
            )

        # Ingest PDF into FAISS
        result = await asyncio.to_thread(
            ingest_pdf,
            file_bytes,
            thread_id,
            file.filename
        )

        return {
            "success": True,
            "message": "PDF uploaded and indexed successfully",
            "thread_id": thread_id,
            "filename": result["filename"],
            "documents": result["documents"],
            "chunks": result["chunks"]
        }

    except HTTPException:
        raise

    except Exception as e:

        print("PDF upload error:", str(e))

        raise HTTPException(
            status_code=500,
            detail=f"PDF processing failed: {str(e)}"
        )

    finally:
        await file.close()


# --------------------------------------------------
# GET DOCUMENT INFORMATION FOR A THREAD
# --------------------------------------------------

@combined_app.get("/document/{thread_id}")
async def get_thread_document(thread_id: str):

    metadata = __THREAD_METADATA.get(str(thread_id))
    print('metadata',metadata)

    if metadata is None:

        raise HTTPException(
            status_code=404,
            detail="No PDF uploaded for this conversation"
        )

    return {
        "filename": metadata["filename"],
        "documents": metadata["documents"],
        "chunks": metadata["chunks"]
    }