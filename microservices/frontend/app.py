import streamlit as st
import uuid
import requests
import json
import sseclient

# Backend base for microservice (default port 8001)
BACKEND_BASE = st.secrets.get("backend_base", "http://127.0.0.1:8001")

st.set_page_config(page_title="Chatbot (microservice)", layout="wide")
st.title("🤖 Chatbot — Microservice Frontend")

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.messages = []

# Helper: fetch history
def fetch_history(thread_id: str):
    try:
        r = requests.get(f"{BACKEND_BASE}/threads/{thread_id}/state", headers={"Accept": "application/json"}, timeout=5)
        if r.status_code == 200:
            return r.json().get("messages", [])
        return []
    except Exception as e:
        st.error(f"Error fetching history: {e}")
        return []

# Render history
st.session_state.messages = fetch_history(st.session_state.thread_id)
for msg in st.session_state.messages:
    role = msg.get("type", "human")
    if role == "ai":
        role = "assistant"
    with st.chat_message(role):
        st.markdown(msg.get("content", ""))

# Send message
if prompt := st.chat_input("What would you like to ask?"):
    with st.chat_message("human"):
        st.markdown(prompt)

    payload = {
        "input": {"messages": [{"type": "human", "content": prompt}]},
        "config": {"thread_id": st.session_state.thread_id}
    }

    with st.chat_message("assistant"):
        placeholder = st.empty()
        text = ""
        try:
            with requests.post(f"{BACKEND_BASE}/stream", json=payload, stream=True, timeout=60) as resp:
                resp.raise_for_status()
                client = sseclient.SSEClient(resp)
                for event in client.events():
                    if event.event == "message":
                        data = json.loads(event.data)
                        messages = data.get("messages", [])
                        # append last AI message content if present
                        if messages and messages[-1].get("type") == "ai":
                            content = messages[-1]["content"]
                            text += content
                            placeholder.markdown(text + "▌")
                    if event.event == "error":
                        err = json.loads(event.data)
                        st.error(f"Stream error: {err.get('error')}")
            placeholder.markdown(text)
        except Exception as e:
            st.error(f"Streaming error: {e}")

    # optional: refresh history from backend
    st.session_state.messages = fetch_history(st.session_state.thread_id)
