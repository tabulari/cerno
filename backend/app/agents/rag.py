"""Qdrant RAG search — used by CodeAnalyst agent."""
import structlog
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

from app.config import get_settings

logger = structlog.get_logger()

_model = None
_qdrant = None


def _get_embedding_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def _get_qdrant() -> QdrantClient:
    global _qdrant
    if _qdrant is None:
        settings = get_settings()
        _qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, timeout=30)
    return _qdrant


def search_codebase(query: str, top_k: int = 5, module_filter: str | None = None) -> list[dict]:
    model = _get_embedding_model()
    client = _get_qdrant()
    settings = get_settings()

    embedding = model.encode(query).tolist()

    query_filter = None
    if module_filter:
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        query_filter = Filter(
            must=[FieldCondition(key="module", match=MatchValue(value=module_filter))]
        )

    try:
        results = client.search(
            collection_name=settings.qdrant_codebase_collection,
            query_vector=embedding,
            limit=top_k,
            query_filter=query_filter,
        )
    except Exception:
        logger.exception("rag.search_failed", query=query[:100])
        return []

    chunks = []
    for hit in results:
        chunks.append({
            "file_path": hit.payload.get("file_path", ""),
            "module": hit.payload.get("module", ""),
            "language": hit.payload.get("language", ""),
            "content": hit.payload.get("content", ""),
            "score": hit.score,
        })

    logger.info("rag.search", query=query[:80], results=len(chunks), module_filter=module_filter)
    return chunks
