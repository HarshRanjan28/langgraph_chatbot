from langgraph.graph import StateGraph,START,END
from langchain_openai import ChatOpenAI
from typing import TypedDict,Literal
from dotenv import load_dotenv
from pydantic import BaseModel,Field

load_dotenv()

model = ChatOpenAI(model="gpt-3.5-turbo")

class SentimentSchema(BaseModel):
    sentiment:Literal["positive","negative"] = Field(description="Sentiment of the review")


structured_model = model.with_structured_output(SentimentSchema)
prompt = "What is the sentiment of the following review - The Software is too bad"
result = structured_model.invoke(prompt).sentiment
print(result)

# Now Defining a State for graph
class ReviewState(TypedDict):
    review:str
    sentiment:Literal["positive","negative"]
    diagnosis:dict
    response:str

def find_sentiment(state:ReviewState):
    prompt = f"For the following review find out the sentiment \n {state["review"]}"
    sentiment = structured_model.invoke(prompt).sentiment
    return {"sentiment":sentiment}

def check_sentiment(state:ReviewState) -> Literal["positive_response","run_diagnosis"]:
    if state["sentiment"] == "positive":
        return "positive_response"
    else:
        return "run_diagnosis"
    
def positive_response(state:ReviewState):
    prompt = f"""
Write a warm thank-you message in response to this review:
\n\n"{state['review']}"\n
Also,kindly ask the user to leave feedback on our website."""
    response = model.invoke(prompt).content
    return {'response',response}

# Defining the graph
graph = StateGraph(ReviewState)
graph.add_node("find_sentiment",find_sentiment)
graph.add_node("positive_response",positive_response)
graph.add_node("run_diagnosis",run_diagnosis)
graph.add_node("negative_response",negative_response)

graph.add_edge(START,"find_sentiment")
graph.add_edge("find_sentiment",END)

workflow = graph.compile()

initial_state = {
    "review":"The product was really bad"
}
workflow.invoke(initial_state)