
import asyncio
from typing import Annotated, Dict, TypedDict,Optional
from dotenv import load_dotenv
from langchain_community.tools import DuckDuckGoSearchResults
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI,OpenAIEmbeddings
from langchain.mcp import MCPAdapter
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
import tempfile
import os

# Load environment variables
load_dotenv()

# Initialize LLM
model = ChatOpenAI(
    model="gpt-4o",
    streaming=True
)

# PDF retriever store (per thread)
__THREAD_RETRIEVERS: Dict[str,any] = {}
__THREAD_METADATA: Dict[str,any] = {}

def _get_retriever(thread_id:Optional[str]):
    """Fetch the retriever for a thread if available"""
    if thread_id and thread_id in __THREAD_RETRIEVERS:
        return __THREAD_RETRIEVERS[thread_id]
    return None

def ingest_pdf(file_bytes:bytes,thread_id:str,filename:Optional[str]):
    """
    Build a FAISS retriever for the uploaded PDF and store it for the thread.
    Returns a summary dict that can be surfaced in the UI.
    """
    if not file_bytes:
        raise ValueError("No file bytes provided for ingestion.")
    
    with tempfile.NamedTemporaryFile(delete=False,suffix='.pdf') as temp_file:
        temp_file.write(file_bytes)
        temp_path = temp_file.name
    
    try:
        # Load the document
        loader = PyPDFLoader(temp_path)
        docs = loader.load()

        # Splitting the document into chunks
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000,chunk_overlap=200,separators=["\n\n","\n"," ",""])
        chunks = splitter.split_documents(docs)

        # Generating embeddings
        embeddings = OpenAIEmbeddings(model='text-embedding-3-small')
        vector_store = FAISS.from_documents(chunks,embeddings)

        # Fetching relevant document with retriever
        retriever = vector_store.as_retriever(search_type='similarity',search_kwargs={'k':1})

        __THREAD_RETRIEVERS[str(thread_id)] = retriever
        print("Thread ID:", thread_id)
        print("_THREAD_RETRIEVERS",__THREAD_RETRIEVERS)

        __THREAD_METADATA[str(thread_id)] = {
            "filename":filename or os.path.basename(temp_path),
            "documents":len(docs),
            "chunks":len(chunks)
        }

        return {
            "filename":filename or os.path.basename(temp_path),
            "documents":len(docs),
            "chunks":len(chunks)
        }

    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass

@tool
def rag_tool(query:str,thread_id:Optional[str] = None) -> dict:
    """
    Retrieve relevant information from the uploaded PDF for this chat thread.
    Always include the thread_id when calling this tool
    """
    
    retriever = _get_retriever(list(__THREAD_RETRIEVERS.keys())[0])
    if retriever is None:
        return {
            "error":"No document indexed for this chat. Upload a PDF first",
            "query":query
        }
    result = retriever.invoke(query)
    context = [doc.page_content for doc in result]
    metadata = [doc.metadata for doc in result]

    return {
        "query":query,
        "context":context,
        "metadata":metadata,
        "source_file": __THREAD_METADATA.get(str(thread_id), {}).get("filename"),
    }
    
# Define calculator tool
@tool
async def calculator(
    first_num: float,
    second_num: float,
    operation: str
) -> dict:
    """
    Perform arithmetic operations on two numbers.

    Supported operations: add, sub, mul, div.
    """

    try:

        if operation == "add":
            result = first_num + second_num

        elif operation == "sub":
            result = first_num - second_num

        elif operation == "mul":
            result = first_num * second_num

        elif operation == "div":

            if second_num == 0:
                return {"error": "Division by zero is not allowed"}

            result = first_num / second_num

        else:
            return {"error": f"Unsupported operation: {operation}"}

        return {
            "first_num": first_num,
            "second_num": second_num,
            "operation": operation,
            "result": result
        }

    except Exception as e:
        return {"error": str(e)}


# Define LangGraph state
class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


# Initialize chatbot asynchronously
async def create_chatbot():

    print("Connecting to MCP server...")

    # Connect to FastMCP server
    async with MCPAdapter(
        "http://127.0.0.1:8000/mcp/"
    ) as adapter:

        # Retrieve MCP tools
        mcp_tools = await adapter.list_tools()

    print("\nMCP tools loaded:")

    for mcp_tool in mcp_tools:
        print(f"- {mcp_tool.name}")

    # Initialize custom tools
    search_tool = DuckDuckGoSearchResults(
        num_results=5
    )

    # Combine all tools
    tools = [
        search_tool,
        calculator,
        *mcp_tools,
        rag_tool
    ]

    print("\nAll available tools:")

    for item in tools:
        print(f"- {item.name}")

    # Bind tools to LLM
    llm_with_tools = model.bind_tools(tools)

    # Chat node
    async def chat_node(state: ChatState):

        messages = state["messages"]

        response = await llm_with_tools.ainvoke(messages)

        return {
            "messages": [response]
        }

    # Initialize graph
    graph = StateGraph(ChatState)

    graph.add_node("chat_node", chat_node)

    graph.add_node(
        "tools",
        ToolNode(tools)
    )

    # Define graph edges
    graph.add_edge(START, "chat_node")

    graph.add_conditional_edges(
        "chat_node",
        tools_condition
    )

    graph.add_edge("tools", "chat_node")

    # Compile graph
    chatbot = graph.compile(
        checkpointer=MemorySaver()
    )

    print("\nLangGraph chatbot initialized successfully!")

    return chatbot


# Optional local testing
async def run_test():

    chatbot = await create_chatbot()

    config = {
        "configurable": {
            "thread_id": "test_session_1"
        }
    }

    inputs = {
        "messages": [
            HumanMessage(
                content="Calculate the bulk discount for "
                        "150 products at $20 each."
            )
        ]
    }

    async for event in chatbot.astream(
        inputs,
        config=config,
        stream_mode="updates"
    ):

        for node, output in event.items():

            print(f"\n--- Node: {node} ---")

            if "messages" in output:
                output["messages"][-1].pretty_print()


if __name__ == "__main__":
    asyncio.run(run_test())
