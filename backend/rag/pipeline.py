"""
RAG Pipeline — Pinecone + OpenAI Embeddings
Handles policy document ingestion, chunking, embedding, and retrieval.

Architecture:
  Documents → Chunker → text-embedding-3-small → Pinecone Index → Retriever → GPT-4o-mini
"""
import os
import json
import time
import logging
import hashlib
from typing import Optional
from openai import AsyncOpenAI
from pinecone import Pinecone, ServerlessSpec

logger = logging.getLogger(__name__)

# ─── Config ──────────────────────────────────────────────────────────────────
PINECONE_API_KEY   = os.environ.get("PINECONE_API_KEY", "")
PINECONE_INDEX     = os.environ.get("PINECONE_INDEX", "yatra-policy")
PINECONE_CLOUD     = os.environ.get("PINECONE_CLOUD", "aws")
PINECONE_REGION    = os.environ.get("PINECONE_REGION", "us-east-1")
EMBED_MODEL        = "text-embedding-3-small"
EMBED_DIMENSIONS   = 1536
TOP_K              = 5
CHUNK_SIZE         = 400   # tokens (approx chars / 4)
CHUNK_OVERLAP      = 80

openai_client = AsyncOpenAI()
_pinecone_index = None


# ─── Pinecone Client ─────────────────────────────────────────────────────────

def get_pinecone_index():
    global _pinecone_index
    if _pinecone_index is not None:
        return _pinecone_index

    pc = Pinecone(api_key=PINECONE_API_KEY)
    existing = [i.name for i in pc.list_indexes()]

    if PINECONE_INDEX not in existing:
        logger.info(f"Creating Pinecone index: {PINECONE_INDEX}")
        pc.create_index(
            name=PINECONE_INDEX,
            dimension=EMBED_DIMENSIONS,
            metric="cosine",
            spec=ServerlessSpec(cloud=PINECONE_CLOUD, region=PINECONE_REGION),
        )
        # Wait for index to be ready
        time.sleep(10)

    _pinecone_index = pc.Index(PINECONE_INDEX)
    logger.info(f"Connected to Pinecone index: {PINECONE_INDEX}")
    return _pinecone_index


# ─── Chunking Strategy ───────────────────────────────────────────────────────

def chunk_text(text: str, source: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[dict]:
    """
    Fixed-size chunking with overlap.
    Strategy: Split on paragraphs first, then enforce max token budget.
    Each chunk carries metadata for citation.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current_chunk = ""
    current_tokens = 0

    for para in paragraphs:
        para_tokens = len(para) // 4  # rough token estimate
        if current_tokens + para_tokens > chunk_size and current_chunk:
            chunk_id = hashlib.md5(f"{source}:{current_chunk[:50]}".encode()).hexdigest()[:12]
            chunks.append({
                "id":     chunk_id,
                "text":   current_chunk.strip(),
                "source": source,
                "tokens": current_tokens,
            })
            # Keep overlap: last N chars of current chunk
            overlap_text = current_chunk[-overlap * 4:]
            current_chunk = overlap_text + "\n\n" + para
            current_tokens = len(current_chunk) // 4
        else:
            current_chunk += "\n\n" + para if current_chunk else para
            current_tokens += para_tokens

    if current_chunk.strip():
        chunk_id = hashlib.md5(f"{source}:{current_chunk[:50]}".encode()).hexdigest()[:12]
        chunks.append({
            "id":     chunk_id,
            "text":   current_chunk.strip(),
            "source": source,
            "tokens": current_tokens,
        })

    logger.info(f"chunked_document source={source} chunks={len(chunks)}")
    return chunks


# ─── Embedding ───────────────────────────────────────────────────────────────

async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Batch embed texts using text-embedding-3-small."""
    response = await openai_client.embeddings.create(
        model=EMBED_MODEL,
        input=texts,
    )
    return [item.embedding for item in response.data]


# ─── Ingestion ───────────────────────────────────────────────────────────────

async def ingest_document(text: str, source: str) -> int:
    """
    Full ingestion pipeline:
      text → chunk → embed → upsert to Pinecone
    Returns number of vectors upserted.
    """
    index = get_pinecone_index()
    chunks = chunk_text(text, source)

    if not chunks:
        logger.warning(f"No chunks produced for source={source}")
        return 0

    # Embed all chunks
    texts = [c["text"] for c in chunks]
    embeddings = await embed_texts(texts)

    # Build Pinecone vectors
    vectors = []
    for chunk, embedding in zip(chunks, embeddings):
        vectors.append({
            "id":     chunk["id"],
            "values": embedding,
            "metadata": {
                "text":   chunk["text"],
                "source": chunk["source"],
                "tokens": chunk["tokens"],
            },
        })

    # Upsert in batches of 100
    batch_size = 100
    for i in range(0, len(vectors), batch_size):
        index.upsert(vectors=vectors[i:i + batch_size])

    logger.info(f"ingested source={source} vectors={len(vectors)}")
    return len(vectors)


async def ingest_file(filepath: str) -> int:
    """Ingest a .txt or .md policy file."""
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()
    source = os.path.basename(filepath)
    return await ingest_document(text, source)


# ─── Retrieval ───────────────────────────────────────────────────────────────

async def retrieve(query: str, top_k: int = TOP_K) -> list[dict]:
    """
    Retrieve top-K relevant chunks for a query.
    Returns list of {id, score, text, source}.
    """
    index = get_pinecone_index()
    query_embedding = await embed_texts([query])

    results = index.query(
        vector=query_embedding[0],
        top_k=top_k,
        include_metadata=True,
    )

    chunks = []
    for match in results.matches:
        chunks.append({
            "id":     match.id,
            "score":  round(match.score, 4),
            "text":   match.metadata.get("text", ""),
            "source": match.metadata.get("source", "unknown"),
        })

    logger.info(f"retrieved query_len={len(query)} chunks={len(chunks)} top_score={chunks[0]['score'] if chunks else 0}")
    return chunks


# ─── RAG Answer Generation ───────────────────────────────────────────────────

RAG_SYSTEM_PROMPT = """You are a corporate travel policy assistant for Yatra.
Answer questions ONLY using the provided policy excerpts below.
Always cite which section/source you're referencing.
If the answer is not in the excerpts, say so clearly — do NOT make up policy.

Respond in JSON:
{
  "answer": "<clear, direct answer based on retrieved policy>",
  "allowed": true|false|null,
  "relevant_policy": "<exact clause from the retrieved context>",
  "suggestion": "<alternative if not allowed, or pro tip>",
  "approval_needed": true|false,
  "sources": ["<source filename>"],
  "retrieval_confidence": 0.0-1.0
}
"""

async def rag_policy_answer(question: str, history: list = []) -> dict:
    """
    Full RAG pipeline: retrieve → augment prompt → generate answer.
    Also logs retrieval to Supabase for eval.
    """
    start = time.time()

    # Step 1: Retrieve relevant chunks
    chunks = await retrieve(question)

    # Step 2: Build augmented context
    context_blocks = []
    for i, chunk in enumerate(chunks, 1):
        context_blocks.append(f"[Excerpt {i} — {chunk['source']} (score: {chunk['score']})]\n{chunk['text']}")
    context = "\n\n---\n\n".join(context_blocks)

    # Step 3: Generate answer with GPT-4o-mini
    messages = [{"role": "system", "content": RAG_SYSTEM_PROMPT}]
    messages.append({"role": "user", "content": f"Policy excerpts:\n{context}\n\nQuestion: {question}"})

    response = await openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.1,
        response_format={"type": "json_object"},
    )

    answer_json = json.loads(response.choices[0].message.content)
    latency_ms = int((time.time() - start) * 1000)

    # Step 4: Log to Supabase for eval/monitoring (non-blocking)
    try:
        from db.supabase_client import get_supabase
        sb = get_supabase()
        sb.table("rag_audit").insert({
            "query":            question,
            "retrieved_chunks": chunks,
            "answer":           answer_json.get("answer", ""),
            "latency_ms":       latency_ms,
        }).execute()
    except Exception as e:
        logger.warning(f"rag_audit_log_failed: {e}")

    answer_json["_meta"] = {
        "chunks_retrieved": len(chunks),
        "latency_ms":       latency_ms,
        "embed_model":      EMBED_MODEL,
    }
    return answer_json
