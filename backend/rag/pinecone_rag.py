"""
RAG Pipeline — Pinecone + OpenAI Embeddings
"""
import os
import re
import logging
from pathlib import Path
from openai import AsyncOpenAI
from pinecone import Pinecone, ServerlessSpec

logger = logging.getLogger(__name__)

PINECONE_API_KEY   = os.environ.get("PINECONE_API_KEY", "")
PINECONE_INDEX     = os.environ.get("PINECONE_INDEX", "yatra-policy")
PINECONE_CLOUD     = os.environ.get("PINECONE_CLOUD", "aws")
PINECONE_REGION    = os.environ.get("PINECONE_REGION", "us-east-1")
EMBED_MODEL        = "text-embedding-3-small"
EMBED_DIMENSIONS   = 1536
CHUNK_SIZE         = 150
CHUNK_OVERLAP      = 60
TOP_K              = 5
POLICY_DOCS_DIR    = Path(__file__).parent.parent.parent / "docs" / "policy_docs"

openai_client = AsyncOpenAI()

_pinecone_index = None

def _get_index():
    global _pinecone_index
    if _pinecone_index is None:
        if not PINECONE_API_KEY:
            raise RuntimeError("PINECONE_API_KEY is not set.")
        pc = Pinecone(api_key=PINECONE_API_KEY)
        existing = [idx.name for idx in pc.list_indexes()]
        if PINECONE_INDEX not in existing:
            logger.info("Creating Pinecone index '%s'...", PINECONE_INDEX)
            pc.create_index(
                name=PINECONE_INDEX,
                dimension=EMBED_DIMENSIONS,
                metric="cosine",
                spec=ServerlessSpec(cloud=PINECONE_CLOUD, region=PINECONE_REGION),
            )
        _pinecone_index = pc.Index(PINECONE_INDEX)
        logger.info("Connected to Pinecone index '%s'.", PINECONE_INDEX)
    return _pinecone_index


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    text = re.sub(r"\n{3,}", "\n\n", text.strip())
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks, current, current_len = [], [], 0
    for sentence in sentences:
        s_len = len(sentence) // 4
        if current_len + s_len > chunk_size and current:
            chunks.append(" ".join(current))
            overlap_sentences, overlap_len = [], 0
            for s in reversed(current):
                overlap_len += len(s) // 4
                if overlap_len >= overlap:
                    break
                overlap_sentences.insert(0, s)
            current, current_len = overlap_sentences, overlap_len
        current.append(sentence)
        current_len += s_len
    if current:
        chunks.append(" ".join(current))
    return [c for c in chunks if c.strip()]


async def _embed(texts: list[str]) -> list[list[float]]:
    response = await openai_client.embeddings.create(
        model=EMBED_MODEL,
        input=texts,
    )
    return [item.embedding for item in response.data]


async def ingest_policy_docs() -> dict:
    """Read all .txt files from docs/policy_docs/, chunk, embed, upsert to Pinecone."""
    index = _get_index()
    all_vectors, total_chunks = [], 0
    BATCH_SIZE = 100

    if not POLICY_DOCS_DIR.exists():
        raise RuntimeError(f"Policy docs directory not found: {POLICY_DOCS_DIR}")

    doc_files = list(POLICY_DOCS_DIR.glob("*.txt"))
    if not doc_files:
        raise RuntimeError(f"No .txt files found in {POLICY_DOCS_DIR}")

    for doc_path in doc_files:
        logger.info("Ingesting: %s", doc_path.name)
        text = doc_path.read_text(encoding="utf-8")
        chunks = _chunk_text(text)
        logger.info("  → %d chunks", len(chunks))

        for i in range(0, len(chunks), 20):
            batch_texts = chunks[i: i + 20]
            embeddings  = await _embed(batch_texts)
            for j, (emb, chunk_text) in enumerate(zip(embeddings, batch_texts)):
                vec_id = f"{doc_path.stem}__chunk_{i+j}"
                all_vectors.append({
                    "id": vec_id,
                    "values": emb,
                    "metadata": {
                        "source": doc_path.name,
                        "chunk_index": i + j,
                        "text": chunk_text,
                    },
                })

        total_chunks += len(chunks)

        for i in range(0, len(all_vectors), BATCH_SIZE):
            index.upsert(vectors=all_vectors[i: i + BATCH_SIZE])
        all_vectors = []

    logger.info("Ingestion complete. Total chunks: %d", total_chunks)
    return {"status": "ok", "chunks_ingested": total_chunks}


async def retrieve_policy(query: str, top_k: int = TOP_K) -> list[dict]:
    """Embed query and retrieve top-K relevant policy chunks from Pinecone."""
    index = _get_index()
    [query_embedding] = await _embed([query])
    results = index.query(
        vector=query_embedding,
        top_k=top_k,
        include_metadata=True,
    )
    chunks = []
    for match in results.matches:
        chunks.append({
            "text":        match.metadata.get("text", ""),
            "source":      match.metadata.get("source", "unknown"),
            "chunk_index": match.metadata.get("chunk_index", 0),
            "score":       round(match.score, 4),
        })
    logger.debug("Retrieved %d chunks for query: %s", len(chunks), query[:60])
    return chunks