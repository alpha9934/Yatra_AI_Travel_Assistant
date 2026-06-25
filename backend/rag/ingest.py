"""
Ingestion Script — Run once (or on policy updates) to populate Pinecone.

Usage:
    python -m rag.ingest

Reads all .txt and .md files from docs/policies/ and upserts to Pinecone.
"""
import asyncio
import os
import sys
import logging

# Ensure backend root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from rag.pipeline import ingest_file

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

POLICY_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "docs", "policies")


async def ingest_all():
    policy_dir = os.path.abspath(POLICY_DIR)
    if not os.path.exists(policy_dir):
        logger.error(f"Policy directory not found: {policy_dir}")
        return

    files = [f for f in os.listdir(policy_dir) if f.endswith((".txt", ".md"))]
    if not files:
        logger.warning("No .txt or .md policy files found in docs/policies/")
        return

    total_vectors = 0
    for fname in files:
        fpath = os.path.join(policy_dir, fname)
        logger.info(f"Ingesting: {fname}")
        count = await ingest_file(fpath)
        total_vectors += count
        logger.info(f"  → {count} vectors upserted")

    logger.info(f"Ingestion complete. Total vectors: {total_vectors}")


if __name__ == "__main__":
    asyncio.run(ingest_all())
