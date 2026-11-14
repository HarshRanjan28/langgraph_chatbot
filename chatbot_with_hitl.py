# imports
from langgraph.graph import StateGraph,START,END
from typing import TypedDict,Annotated,Literal
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage,HumanMessage
from dotenv import load_dotenv
from langgraph.graph.message import add_messages
from langchain_core.tools import tool
from langgraph.types import interrupt,Command
from langgraph.prebuilt import ToolNode,tools_condition

load_dotenv()

model = ChatOpenAI(model='gpt-4o')

class ChatState(TypedDict):
    messages:Annotated[list[BaseMessage],add_messages]


# Custom tools
@tool
def purchase_stock(symbol:str,quantity:int) -> dict:
    """
    Simulate purchasing a given quantity of a stock symbol.

    HUMAN-IN-THE-LOOP:
    Before confirming the purchase,this tool will interrupt
    and wait for a human decision ("yes"/anything else)
    """
    decision = interrupt(f"Approve buying {quantity} shares of {symbol}? (yes/no)")

    if decision.strip().lower() == "yes":
        return {
            "status":"success",
            "message":f"Purchase order placed for {quantity} shares of {symbol}",
            "symbol":symbol,
            "quantity":quantity
        }
    else:
        return {
            "status":"cancelled",
            "message":f"Purchase of {quantity} shares of the {symbol} was declined",
            "symbol":symbol,
            "quantity":quantity
        }
    
tools = [purchase_stock]
    
llm_with_tools = model.bind_tools(tools)

def chat_node(state:ChatState):
    """LLM node that may answer a question or request a tool call"""
    messages = state['messages']
    response = llm_with_tools.invoke(messages)
    return {"messages":[response]}

tool_node = ToolNode(tools)

graph = StateGraph(ChatState)
graph.add_node("chat_node",chat_node)
graph.add_node("tools",tool_node)

graph.add_edge(START,"chat_node")
graph.add_conditional_edges("chat_node",tools_condition)
graph.add_edge("tools","chat_node")

chatbot = graph.compile()

if __name__ == "__main__":
    thread_id = "thread_1"

    while True:
        user_input = input("You: ")

        state = {"messages":[HumanMessage(content=user_input)]}

        result = chatbot.invoke(
            state,
            config={"configurable":{"thread_id":thread_id}}
        )

        interuppts = result.get("__interrupt__",[])

        if interuppts:

            prompt_to_human = interuppts[0].value
            print(f"HITL: {prompt_to_human}")
            decision = input("Your decision: ").strip().lower()

            result = chatbot.invoke(
                Command(resume=decision),
                config={"configurable":{"thread_id":thread_id}}
            )
        messgaes = result['messages']
        last_msg = messgaes[-1]
        print(f"Bot: {last_msg.content}")


