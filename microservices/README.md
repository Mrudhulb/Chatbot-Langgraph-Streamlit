Microservices folder

Structure:

- backend/server.py  -> FastAPI microservice (port 8001 by default)
- frontend/app.py   -> Streamlit frontend that talks to backend

Run backend:

1. Activate your virtual environment
2. cd Streamlit/microservices/backend
3. uvicorn server:app --reload --port 8001

Run frontend:

1. Activate venv
2. cd Streamlit/microservices/frontend
3. streamlit run app.py

Notes:
- The backend loads your existing `Streamlit/backend/graph.py` dynamically. Make sure that file exports `compiled_graph` and (optionally) `memory`.
- The backend's `invoke` and `stream` endpoints expect the JSON shape:
  {
    "input": { "messages": [{"type": "human", "content": "..."}] },
    "config": {"thread_id": "..."}
  }
- If your `compiled_graph.invoke()` signature is different, update `server.py` to adapt the call shapes.
- The frontend defaults to `http://127.0.0.1:8001`. Change with Streamlit secrets `backend_base` if needed.

If you want, I can also patch `Streamlit/backend/graph.py` to export `compiled_graph` and `memory` in a more compatible way — tell me if you'd like that.