"""Central configuration. All paths are absolute (derived from this file),
so the app works regardless of the current working directory."""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

ACCOUNT_ID = "cultpass"
CULTPASS_DB = BASE_DIR / "data" / "external" / "cultpass.db"
UDAHUB_DB = BASE_DIR / "data" / "core" / "udahub.db"
MEMORY_DB = BASE_DIR / "data" / "core" / "memory.db"
CHECKPOINT_DB = BASE_DIR / "data" / "core" / "checkpoints.db"
KB_EMBEDDING_CACHE = BASE_DIR / "data" / "core" / "kb_embeddings.json"
LOG_FILE = BASE_DIR / "logs" / "agent_events.jsonl"

LLM_MODEL = os.getenv("UDAHUB_LLM_MODEL", "gpt-4o-mini")
EMBED_MODEL = os.getenv("UDAHUB_EMBED_MODEL", "text-embedding-3-small")

# Decision thresholds (see agentic/design/architecture.md)
CLASSIFIER_MIN_CONFIDENCE = float(os.getenv("CLASSIFIER_MIN_CONFIDENCE", 0.5))
KB_MIN_SIMILARITY = float(os.getenv("KB_MIN_SIMILARITY", 0.30))
KB_CONFIDENCE_THRESHOLD = float(os.getenv("KB_CONFIDENCE_THRESHOLD", 0.50))


def get_llm(temperature: float = 0.0):
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(model=LLM_MODEL, temperature=temperature)


def get_embeddings():
    from langchain_openai import OpenAIEmbeddings
    return OpenAIEmbeddings(model=EMBED_MODEL)
