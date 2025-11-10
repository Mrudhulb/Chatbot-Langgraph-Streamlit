"""
Microservice backend wrapping the existing LangGraph `graph.py`.
This server dynamically loads the repo's `Streamlit/backend/graph.py` module and
exposes these endpoints:

- POST /invoke  -> non-streaming invoke
- POST /stream  -> streaming invoke (SSE)
- GET  /threads/{thread_id}/state -> return saved messages + summary
- DELETE /threads/{thread_id} -> delete saved thread state

Run:
    python server.py
or
    uvicorn server:app --reload --port 8001

This file avoids direct package imports of graph by loading the file by path
so it works regardless of working directory.
"""
from pathlib import Path
import importlib.util
import json
import asyncio
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

# Load repo's graph.py by path so imports are robust regardless of cwd
HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent  # Streamlit/microservices -> Streamlit -> repo root (parent of Streamlit)
GRAPH_PATH = REPO_ROOT / "backend" / "graph.py"  # points to Streamlit/backend/graph.py

if not GRAPH_PATH.exists():
    # Try alternative location (if repo layout differs)
    GRAPH_PATH = REPO_ROOT.parent / "Streamlit" / "backend" / "graph.py"

if not GRAPH_PATH.exists():
    raise FileNotFoundError(f"Could not locate graph.py at expected path(s). Looked at: {GRAPH_PATH}")

spec = importlib.util.spec_from_file_location("_remote_graph", str(GRAPH_PATH))
graph_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(graph_mod)  # type: ignore

# Expect graph_mod to export `compiled_graph` and `memory` (the MemorySaver)
if not hasattr(graph_mod, "compiled_graph"):
    raise ImportError("graph.py must expose `compiled_graph` (compiled graph object)")
compiled_graph = getattr(graph_mod, "compiled_graph")
memory = getattr(graph_mod, "memory", None)

# --- FastAPI app ---
app = FastAPI(title="LangGraph Microservice Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class Message(BaseModel):
    type: str
    content: str

class InputPayload(BaseModel):
    messages: list[Message]

class InvokeRequest(BaseModel):
    input: InputPayload
    config: Dict[str, Any] | None = None

# Helpers
def _serialize_message(msg: Any) -> Dict[str, str]:
    """Convert any message type to a serializable dict with content."""
    # Handle LangChain message objects
    if hasattr(msg, 'content'):
        # Check for specific message types
        msg_type = type(msg).__name__
        if msg_type == "AIMessage":
            return {"type": "ai", "content": str(msg.content)}
        elif msg_type == "HumanMessage":
            return {"type": "human", "content": str(msg.content)}
        else:
            return {"type": "human", "content": str(msg.content)}
    # Handle dict messages
    elif isinstance(msg, dict):
        return {
            "type": msg.get("type", "human"),
            "content": str(msg.get("content", ""))
        }
    # Handle string or other types
    return {
        "type": "human",  # default type
        "content": str(msg)
    }

def _serialize_messages(messages: list[Any]) -> list[Dict[str, str]]:
    """Convert a list of messages to serializable format."""
    return [_serialize_message(msg) for msg in messages]

def _to_graph_config(cfg: Dict[str, Any] | None) -> Dict[str, Any]:
    """Convert a simple config into the `configurable` shape LangGraph expects."""
    if not cfg:
        return {}
    # Accept either {"thread_id": "..."} or full configurable dict
    if "thread_id" in cfg:
        return {"configurable": {"thread_id": cfg["thread_id"]}}
    if "configurable" in cfg:
        return cfg
    return {"configurable": cfg}

# Endpoints
@app.post("/invoke")
async def invoke(req: InvokeRequest):
    try:
        input_dict = {"messages": [m.dict() for m in req.input.messages]}
        config = _to_graph_config(req.config)
        # compiled_graph.invoke may expect (input_data, config=config)
        resp = compiled_graph.invoke(input_dict, config=config)
        messages = _serialize_messages(resp.get("messages", []))
        return {"messages": messages, "state": resp.get("state", {})}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/stream")
async def stream(req: InvokeRequest, request: Request):
    """Stream a single JSON data SSE message after running the graph.
    If your graph supports incremental events you can adapt this generator.
    """
    async def generator():
        try:
            print("Starting stream processing...")  # Debug print
            input_dict = {"messages": [m.dict() for m in req.input.messages]}
            config = _to_graph_config(req.config)
            
            # Run the graph (synchronous call in user repo)
            print(f"Input message: '{input_dict['messages'][-1]['content']}'")  # Just print the last message
            resp = compiled_graph.invoke(input_dict, config=config)
            
            # Serialize messages
            messages = _serialize_messages(resp.get("messages", []))
            
            # Print only the last human and AI messages for clarity
            for msg in messages[-2:]:  # Get last 2 messages
                print(f"{msg['type'].upper()}: '{msg['content'][:100]}{'...' if len(msg['content']) > 100 else ''}'")
            
            # Prepare SSE data
            data = {
                "node": "conversation",
                "messages": messages,
                "state": resp.get("state", {})
            }
            
            # Send event
            yield "event: message\n"
            yield f"data: {json.dumps(data)}\n\n"
            print("Stream response sent successfully")  # Debug print
            
        except Exception as e:
            print(f"Error in stream processing: {str(e)}")  # Debug print
            err = {"error": str(e)}
            yield "event: error\n"
            yield f"data: {json.dumps(err)}\n\n"

    return EventSourceResponse(generator())

@app.get("/threads/{thread_id}/state")
async def get_thread_state(thread_id: str):
    try:
        cfg = {"configurable": {"thread_id": thread_id}}
        state = compiled_graph.get_state(cfg)
        messages = _serialize_messages(state.values.get("messages", []))
        return {"messages": messages, "summary": state.values.get("summary", "")}
    except Exception as e:
        # If no state exists, return empty
        return {"messages": [], "summary": ""}

@app.delete("/threads/{thread_id}")
async def delete_thread(thread_id: str):
    if memory is None:
        raise HTTPException(status_code=500, detail="Memory saver not available in graph module")
    try:
        memory.delete_state({"configurable": {"thread_id": thread_id}})
        return {"status": "deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8001, reload=True)
