"""Standalone CLI query runner for CampusMate Hybrid RAG.
Called by Express server if FastAPI service on port 8010 is temporarily unreachable.
"""
import json
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parents[2]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.retrieval.hybrid_engine import HybridRAGEngine


def main():
    question = ""
    conv_id = None
    history = None
    model = None

    if len(sys.argv) > 1 and sys.argv[1].strip():
        question = sys.argv[1].strip()
        conv_id = sys.argv[2].strip() if len(sys.argv) > 2 and sys.argv[2].strip() else None
    else:
        try:
            stdin_data = sys.stdin.read().strip()
            if stdin_data:
                payload = json.loads(stdin_data)
                question = payload.get("question") or payload.get("message", "")
                conv_id = payload.get("conversation_id")
                history = payload.get("history")
                model = payload.get("model")
        except Exception:
            pass

    if not question:
        print(json.dumps({"error": "No query provided"}))
        return

    engine = HybridRAGEngine.get_instance()
    result = engine.answer_query(question, conversation_id=conv_id, history=history, model=model)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
