from typing import TypedDict
from langgraph.graph import StateGraph,START,END
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

subgraph_model = ChatOpenAI(model='gpt-4o')

class SubState(TypedDict):
    input_txt:str
    translated_txt:str

def translate_text(state:SubState):
    prompt = f"""
    Translate the following text to Hindi.
    Keep it natural and clear.Do not add extra comment.

    Text:
    {state['input_txt']}
    """.strip()

    translated_text = subgraph_model.invoke(prompt).content

    return {"translated_txt":translated_text}

subgraph_builder = StateGraph(SubState)

subgraph_builder.add_node("translate_text",translate_text)
subgraph_builder.add_edge(START,"translate_text")
subgraph_builder.add_edge("translate_text",END)

subgraph = subgraph_builder.compile()