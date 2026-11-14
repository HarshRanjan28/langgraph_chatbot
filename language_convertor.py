from typing import TypedDict
from langgraph.graph import StateGraph,START,END
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from subgraph_langgraph import subgraph

load_dotenv()

llm = ChatOpenAI(model='gpt-4o')

class ParentState(TypedDict):
    question:str
    answer_eng:str
    answer_hin:str

graph = StateGraph(ParentState)

def generate_answer(state:ParentState):
    prompt = f"You are a helpful assistant. Answer clearly. \n\nQuestion: {state['question']}"
    answer = llm.invoke(prompt).content

    return {"answer_eng":answer}

def translate_answer(state:ParentState):
    
    # Call the subgraph
    result = subgraph.invoke({"input_txt":state['answer_eng']})
    return {"answer_hin":result['translated_txt']}

graph.add_node("answer",generate_answer)
graph.add_node("translate",translate_answer)

graph.add_edge(START,"answer")
graph.add_edge("answer","translate")
graph.add_edge("translate",END)

graph_translator = graph.compile()

result = graph_translator.invoke({"question":"What is quantum physics"})
print(result['answer_hin'])
