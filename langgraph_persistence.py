from langgraph.graph import StateGraph, START, END
from typing import TypedDict
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from langgraph.checkpoint.memory import InMemorySaver

load_dotenv()

model = ChatOpenAI(model='gpt-4o')

class JokeState(TypedDict):
    topic:str
    joke:str
    explanation:str


def generate_joke(state:JokeState):
    prompt = f"generate a joke on the topic {state['topic']}"
    response = model.invoke(prompt).content

    return {'joke':response}

def generate_explanation(state:JokeState):
    prompt = f"write a explanation for the topic - {state['topic']}"
    response = model.invoke(prompt).content
    
    return {'explanation':response}

graph = StateGraph(JokeState)

graph.add_node('generate_joke',generate_joke)
graph.add_node('generate_explanation',generate_explanation)

graph.add_edge(START,'generate_joke')
graph.add_edge('generate_joke','generate_explanation')
graph.add_edge('generate_explanation',END)

# Implementing persistence
checkpointer = InMemorySaver()

workflow = graph.compile(checkpointer=checkpointer)

config1 = {'configurable':{"thread_id":'1'}}
result = workflow.invoke({'topic':'pizza'},config=config1)
print(result)