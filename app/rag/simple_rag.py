from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from app.schemas.models import RagHit

DOCS_DIR = Path(__file__).resolve().parents[2] / "docs"

@dataclass
class DocumentChunk:
    doc_id: str
    source: str
    text: str

class SimpleRagIndex:
    def __init__(self) -> None:
        self.chunks: List[DocumentChunk] = []
        self.vectorizer = TfidfVectorizer(stop_words="english")
        self.matrix = None

    def build(self) -> None:
        self.chunks = []
        for path in sorted(DOCS_DIR.glob("*")):
            if path.suffix.lower() not in {".md", ".txt"}:
                continue
            text = path.read_text(encoding="utf-8")
            for i, chunk in enumerate(self._chunk_text(text)):
                self.chunks.append(DocumentChunk(doc_id=f"{path.stem}-{i}", source=path.name, text=chunk))
        if not self.chunks:
            self.matrix = None
            return
        self.matrix = self.vectorizer.fit_transform([c.text for c in self.chunks])

    def search(self, query: str, top_k: int = 3) -> List[RagHit]:
        if self.matrix is None or not self.chunks:
            self.build()
        if self.matrix is None or not self.chunks:
            return []
        q = self.vectorizer.transform([query])
        scores = cosine_similarity(q, self.matrix).flatten()
        top_idx = scores.argsort()[::-1][:top_k]
        return [
            RagHit(doc_id=self.chunks[i].doc_id, source=self.chunks[i].source, score=float(scores[i]), text=self.chunks[i].text)
            for i in top_idx if scores[i] > 0
        ]

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
