import os
import logging
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings

from app.services.nlp_service import nlp_service

logger = logging.getLogger(__name__)


class VectorService:
    """
    Simple Chroma-backed vector store for per-session search over OCR text.
    Uses Gemini embeddings via nlp_service.embed_text.
    """

    def __init__(self, persist_path: str = "chroma"):
        os.makedirs(persist_path, exist_ok=True)
        self.client = chromadb.PersistentClient(path=persist_path, settings=Settings(allow_reset=False))

    def _collection_name(self, session_id: str) -> str:
        return f"session-{session_id}"

    def get_collection(self, session_id: str):
        return self.client.get_or_create_collection(
            name=self._collection_name(session_id),
            metadata={"hnsw:space": "cosine"},
        )

    def upsert_document(
        self,
        session_id: str,
        document_id: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Embed OCR text and store in Chroma."""
        if not text:
            logger.warning("Empty text for document %s; skipping vector upsert", document_id)
            return

        emb = nlp_service.embed_text(text)
        if not emb:
            logger.warning("No embedding returned for document %s; skipping vector upsert", document_id)
            return

        collection = self.get_collection(session_id)
        collection.upsert(
            ids=[document_id],
            embeddings=[emb],
            documents=[text],
            metadatas=[metadata or {}],
        )
        logger.info("Upserted vectors for doc %s in session %s", document_id, session_id)

    def search(
        self,
        session_id: str,
        query: str,
        top_k: int = 10,
    ) -> Dict[str, Any]:
        """Vector search by embedding the query text."""
        if not query:
            return {"ids": [], "distances": [], "metadatas": [], "documents": []}

        emb = nlp_service.embed_text(query)
        if not emb:
            logger.warning("No embedding returned for query; returning empty search result")
            return {"ids": [], "distances": [], "metadatas": [], "documents": []}

        collection = self.get_collection(session_id)
        res = collection.query(
            query_embeddings=[emb],
            n_results=top_k,
        )
        return res


vector_service = VectorService()
