# imports
from langgraph.graph import StateGraph,START,END
from typing import TypedDict,Annotated,Literal
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage,HumanMessage
from dotenv import load_dotenv
from langgraph.graph.message import add_messages

load_dotenv()

model = ChatOpenAI(model='gpt-4o')

# Defining the state
class ChatState(TypedDict):
    messages : Annotated[list[BaseMessage],add_messages]

def chat_node(state:ChatState):
    # take user query from state
    messages = state['messages']
    
    # send to LLM
    response = model.invoke(messages)

    # response store state
    return {'messages':[response]}

# Defining the graph
graph = StateGraph(ChatState)

# Add nodes
graph.add_node('chat_node',chat_node)

# add edge
graph.add_edge(START,'chat_node')
graph.add_edge('chat_node',END)

# compiling the graph
chatbot = graph.compile()

# executing the graph
while True:
    user_message = input("Type here: ")
    print('User: ',user_message)

    if user_message.strip().lower() in ['exit','quit','bye']:
        break

    response = chatbot.invoke({'messages':[HumanMessage(content=user_message)]})
    print("AI: ",response['messages'][-1].content)
