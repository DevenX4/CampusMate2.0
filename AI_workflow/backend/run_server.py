import sys
import os
from pathlib import Path
import uvicorn

# Ensure backend root is always on sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

if __name__ == "__main__":
    port = int(os.environ.get("AI_PORT", 8010))
    print(f"[AI WORKFLOW] Booting CampusMate Hybrid RAG FastAPI server on http://127.0.0.1:{port} ...", flush=True)
    from app.main import app
    print(f"[AI WORKFLOW] FastAPI app loaded successfully. Starting Uvicorn engine on port {port}...", flush=True)
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
