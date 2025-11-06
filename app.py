import streamlit as st
import uuid
import os
import urllib.request
from dotenv import load_dotenv

from typing import Literal
from langchain_core.messages import HumanMessage, SystemMessage, RemoveMessage, AIMessage
from langgraph.graph import MessagesState, StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_google_genai import ChatGoogleGenerativeAI

# --- 1. Page Configuration ---
st.set_page_config(
    page_title="My Chatbot (with MemorySaver)",
    page_icon="🤖",
    layout="wide"
)
st.title("🤖 My Chatbot (with MemorySaver)")

# --- 2. Load Environment Variables ---
# Make sure you have a .env file in this directory
env_path = ".env"  # Assumes .env is in the same folder
load_dotenv()
api_key = st.secrets.get("GOOGLE_API_KEY")

if not api_key:
    st.error("Please add your GOOGLE_API_KEY to Streamlit secrets!")
    st.stop()

# --- 3. Download and Connect to SQLite Database ---
# (This replaces the shell commands from your example)

# db_dir = "state_db"
# db_path = os.path.join(db_dir, "example.db")
# db_url = "https://github.com/langchain-ai/langchain-academy/raw/main/module-2/state_db/example.db"

# Create directory if it doesn't exist
# if not os.path.exists(db_dir):
#     os.makedirs(db_dir)

# Download the database file if it doesn't exist
if not os.path.exists(db_path):
    with st.spinner(f"Downloading database from {db_url}..."):
        urllib.request.urlretrieve(db_url, db_path)
    st.success("Database downloaded.")

# Connect to the database
# conn = sqlite3.connect(db_path, check_same_thread=False)

# --- 4. Define Graph and State (from chatbot.py) ---
#

# Define the model
model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0, api_key=api_key)

# State class to store messages and summary
class State(MessagesState):
    summary: str

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

# --- 5. Compile the Graph with SQLite Checkpointer ---

@st.cache_resource
def get_graph():
    """
    Compile the graph and cache it as a Streamlit resource.
    """
    workflow = StateGraph(State)
    workflow.add_node("conversation", call_model)
    workflow.add_node(summarize_conversation)
    workflow.add_edge(START, "conversation")
    workflow.add_conditional_edges("conversation", should_continue)
    workflow.add_edge("summarize_conversation", END)
    
    # Use the SqliteSaver
    # memory = SqliteSaver(conn)
    
    # Compile the graph
    graph = workflow.compile(checkpointer=MemoorySaver())
    return graph

graph = get_graph()

# --- 6. Streamlit Chat Interface Logic ---

# Ensure a unique thread_id is created for each new session
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

# Use the thread_id to load the chat history from the database
config = {"configurable": {"thread_id": st.session_state.thread_id}}

try:
    # Get the current state from the database
    thread_state = graph.get_state(config)
    # Load messages from the saved state
    st.session_state.messages = thread_state.values.get("messages", [])
except:
    # Handle cases where the thread doesn't exist yet
    st.session_state.messages = []

# Display all stored messages
for message in st.session_state.messages:
    # Messages from the DB are objects (HumanMessage, AIMessage)
    if message.type == "human":
        with st.chat_message("human"):
            st.markdown(message.content)
    elif message.type == "ai":
        with st.chat_message("assistant"):
            st.markdown(message.content)

# Get user input from the chat box
if prompt := st.chat_input("What would you like to ask?"):
    
    # 1. Display the user's message
    with st.chat_message("human"):
        st.markdown(prompt)

    # 2. Format the input for the LangGraph
    # We use the tuple format (type, content) which MessagesState understands
    input_data = {"messages": [("human", prompt)]}
    
    # 3. Call the graph.invoke() directly (NO client needed)
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        
        try:
            # .invoke() runs the graph and waits for the final state
            response = graph.invoke(input_data, config=config)
            
            # 4. Extract the last AI message from the final state
            ai_message = response["messages"][-1]
            response_placeholder.markdown(ai_message.content)

        except Exception as e:
            error_message = f"Error communicating with the graph: {e}"
            st.error(error_message)
