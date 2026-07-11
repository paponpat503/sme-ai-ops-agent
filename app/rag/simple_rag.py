from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List, Protocol
import hashlib
import threading
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from app.schemas.models import RagHit
from app.config import get_settings

DOCS_DIR = Path(__file__).resolve().parents[2] / "docs"
KNOWLEDGE_FILES = {"company_policy.md", "onboarding_playbook.md"}


class Retriever(Protocol):
    def build(self) -> None: ...
    def search(self, query: str, top_k: int = 3, tenant_id: str = "demo") -> List[RagHit]: ...
    def is_ready(self) -> bool: ...

@dataclass
class DocumentChunk:
    doc_id: str
    source: str
    text: str
    section: str
    version: str

class SimpleRagIndex:
    def __init__(self) -> None:
        self.chunks: List[DocumentChunk] = []
        self.vectorizer = TfidfVectorizer(stop_words="english")
        self.matrix = None
        self._lock = threading.RLock()

    def build(self) -> None:
        with self._lock:
            chunks: List[DocumentChunk] = []
            for path in sorted(DOCS_DIR.glob("*")):
                if path.name not in KNOWLEDGE_FILES:
                    continue
                text = path.read_text(encoding="utf-8")
                version = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
                for chunk in self._chunk_text(text):
                    section = self._section_name(chunk)
                    stable = hashlib.sha256(f"{path.name}:{section}:{chunk}".encode("utf-8")).hexdigest()[:12]
                    chunks.append(DocumentChunk(doc_id=f"{path.stem}-{stable}", source=path.name, text=chunk, section=section, version=version))
            if not chunks:
                self.chunks = []
                self.matrix = None
                return
            vectorizer = TfidfVectorizer(stop_words="english")
            matrix = vectorizer.fit_transform([chunk.text for chunk in chunks])
            self.chunks = chunks
            self.vectorizer = vectorizer
            self.matrix = matrix

    def search(self, query: str, top_k: int = 3, tenant_id: str = "demo") -> List[RagHit]:
        if tenant_id != "demo":
            return []
        if self.matrix is None or not self.chunks:
            self.build()
        if self.matrix is None or not self.chunks:
            return []
        with self._lock:
            chunks = list(self.chunks)
            matrix = self.matrix
            q = self.vectorizer.transform([query])
        scores = cosine_similarity(q, matrix).flatten()
        top_idx = scores.argsort()[::-1][:top_k]
        return [
            RagHit(
                doc_id=chunks[i].doc_id,
                source=chunks[i].source,
                score=float(scores[i]),
                text=chunks[i].text,
                tenant_id=tenant_id,
                section=chunks[i].section,
                version=chunks[i].version,
            )
            for i in top_idx if scores[i] >= get_settings().retrieval_min_score
        ]

    def is_ready(self) -> bool:
        return self.matrix is not None and bool(self.chunks)

    @staticmethod
    def _section_name(text: str) -> str:
        for line in text.splitlines():
            if line.startswith("#"):
                return line.lstrip("#").strip()
        return "document"

    @staticmethod
    def _chunk_text(text: str, max_chars: int = 800) -> List[str]:
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        chunks: List[str] = []
        current = ""
        for p in paragraphs:
            if len(current) + len(p) + 2 <= max_chars:
                current = (current + "\n\n" + p).strip()
            else:
                if current:
                    chunks.append(current)
                current = p
        if current:
            chunks.append(current)
        return chunks

rag_index = SimpleRagIndex()
