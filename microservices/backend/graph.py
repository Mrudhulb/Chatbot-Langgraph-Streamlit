import os
from typing import Literal, Optional
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage, RemoveMessage, AIMessage
from langgraph.graph import MessagesState, StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_google_genai import ChatGoogleGenerativeAI

# Load environment variables
# Get the directory where this file (graph.py) is located
script_dir = os.path.dirname(os.path.abspath(__file__))
# Join that directory path with the .env file name
env_path = os.path.join(script_dir, '.env')

# Explicitly load that file
load_dotenv(dotenv_path=env_path)

api_key = os.environ.get("GOOGLE_API_KEY")

if not api_key:
    # Give a more specific error message
    raise ValueError(f"GOOGLE_API_KEY not found in {env_path}. Make sure the file exists and is not empty.")
if not api_key:
    print('GOOGLE_API_KEY not found in .env file')
    raise ValueError("GOOGLE_API_KEY not found in .env file")

# --- 4. Define Graph and State (from app.py) ---
# [cite: app.py]

# Define the model
model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0, google_api_key=api_key)

# State class to store messages and summary
class State(MessagesState):
    summary: Optional[str] = None # <-- 2. Make summary optional

# Define the logic to call the model
def call_model(state: State):
    summary = state.get("summary", "")
    if summary:
        system_message = f"Summary of conversation earlier: {summary}"
        messages = [SystemMessage(content=system_message)] + state["messages"]
    else:
        messages = state["messages"]
    
    response = model.invoke(messages)
    # Ensure the response is wrapped in a list for MessagesState
    return {"messages": [response]}

# Determine whether to end or summarize the conversation
def should_continue(state: State) -> Literal["summarize_conversation", "__end__"]:
    messages = state["messages"]
    if len(messages) > 6:
        return "summarize_conversation"
    return END

def summarize_conversation(state: State):
    summary = state.get("summary", "")
    if summary:
        summary_message = (
            f"This is summary of the conversation to date: {summary}\n\n"
            "Extend the summary by taking into account the new messages above:"
        )
    else:
        summary_message = "Create a summary of the conversation above:"

    messages = state["messages"] + [HumanMessage(content=summary_message)]
    response = model.invoke(messages)
    
    delete_messages = [RemoveMessage(id=m.id) for m in state["messages"][:-2]]
    return {"summary": response.content, "messages": delete_messages}

# Create the memory saver that will be used for persistence
memory = MemorySaver()

# --- 5. Compile the Graph ---
def get_graph():
    workflow = StateGraph(State)
    workflow.add_node("conversation", call_model)
    workflow.add_node(summarize_conversation)
    workflow.add_edge(START, "conversation")
    workflow.add_conditional_edges("conversation", should_continue)
    workflow.add_edge("summarize_conversation", END)
    
    # Use the shared memory saver for persistence
    graph = workflow.compile(checkpointer=memory)
    return graph

# This is the compiled graph that server.py will import
compiled_graph = get_graph()