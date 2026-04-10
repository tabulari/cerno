"""Codebase indexer — embeds chunks.json into Qdrant.
Run as: python -m app.indexer
"""
import json
import os
import sys

import structlog

structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger()


def main():
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct

    host = os.getenv("QDRANT_HOST", "qdrant")
    port = int(os.getenv("QDRANT_PORT", "6333"))
    collection = os.getenv("QDRANT_CODEBASE_COLLECTION", "codebase")

    logger.info("indexer.start", host=host, port=port, collection=collection)

    client = QdrantClient(host=host, port=port, timeout=60)

    collections = [c.name for c in client.get_collections().collections]
    if collection in collections:
        info = client.get_collection(collection)
        if info.points_count > 0:
            logger.info("indexer.skip", collection=collection, points=info.points_count)
            sys.exit(0)

    chunks_path = os.path.join(os.path.dirname(__file__), "..", "data", "chunks.json")
    if not os.path.exists(chunks_path):
        logger.warning("indexer.no_chunks", path=chunks_path)
        logger.info("indexer.creating_sample_chunks")
        os.makedirs(os.path.dirname(chunks_path), exist_ok=True)
        sample_chunks = [
            {
                "file_path": "src/checkout/cart.js",
                "language": "javascript",
                "module": "checkout",
                "type": "source",
                "content": "const addToCart = async (productId, quantity) => {\n  const pool = getPool();\n  const conn = await pool.connect();\n  try {\n    await conn.query('INSERT INTO cart_items ...');\n  } finally {\n    conn.release();\n  }\n};",
            },
            {
                "file_path": "src/db/pool.js",
                "language": "javascript",
                "module": "database",
                "type": "source",
                "content": "const { Pool } = require('pg');\nconst pool = new Pool({\n  max: 10,\n  connectionTimeoutMillis: 3000,\n  idleTimeoutMillis: 30000,\n});\nmodule.exports = { getPool: () => pool };",
            },
            {
                "file_path": "src/payments/stripe.js",
                "language": "javascript",
                "module": "payments",
                "type": "source",
                "content": "const stripe = require('stripe')(process.env.STRIPE_KEY);\nconst createCharge = async (amount, currency, source) => {\n  return stripe.charges.create({ amount, currency, source });\n};",
            },
        ]
        with open(chunks_path, "w") as f:
            json.dump(sample_chunks, f, indent=2)

    with open(chunks_path) as f:
        chunks = json.load(f)

    logger.info("indexer.embedding", chunks=len(chunks))

    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("all-MiniLM-L6-v2")
    texts = [c["content"] for c in chunks]
    embeddings = model.encode(texts, show_progress_bar=True)
    dim = embeddings.shape[1]

    if collection not in collections:
        client.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )

    points = [
        PointStruct(
            id=i,
            vector=embeddings[i].tolist(),
            payload={
                "file_path": chunks[i].get("file_path", ""),
                "language": chunks[i].get("language", ""),
                "module": chunks[i].get("module", ""),
                "type": chunks[i].get("type", ""),
                "content": chunks[i]["content"],
            },
        )
        for i in range(len(chunks))
    ]

    batch_size = 100
    for i in range(0, len(points), batch_size):
        client.upsert(collection_name=collection, points=points[i:i + batch_size])

    logger.info("indexer.complete", collection=collection, points=len(points), dimensions=dim)


if __name__ == "__main__":
    main()
