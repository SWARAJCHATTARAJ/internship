import json
import os
from typing import Optional, Tuple

from schemas.core import GroundedConcept
from tools.hf_models import get_embedding_model

try:
    import chromadb
    from chromadb.config import Settings
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover
    chromadb = None
    Settings = None
    SentenceTransformer = None


_DATA_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'ontology_seed.json')
_INDEX_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'ontology_index')
_EMBEDDING_MODEL_NAME = "NeuML/biomedbert-base-embeddings"


def _load_seed_entries():
    if not os.path.exists(_DATA_PATH):
        return []
    with open(_DATA_PATH, 'r', encoding='utf-8') as handle:
        return json.load(handle)


def build_ontology_index(force: bool = False):
    if chromadb is None or SentenceTransformer is None:
        return None
    if os.path.exists(_INDEX_PATH) and not force:
        return _INDEX_PATH

    entries = _load_seed_entries()
    if not entries:
        return None

    client = chromadb.PersistentClient(path=_INDEX_PATH)
    collection = client.get_or_create_collection("ontology")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    documents = []
    metadatas = []
    ids = []
    for idx, entry in enumerate(entries):
        text = f"{entry.get('name', '')} {entry.get('description', '')}"
        documents.append(text)
        metadatas.append({
            "name": entry.get("name", ""),
            "code": entry.get("code", ""),
            "ontology": entry.get("ontology", ""),
            "description": entry.get("description", ""),
        })
        ids.append(f"entry-{idx}")

    embeddings = model.encode(documents, convert_to_numpy=True)
    collection.add(documents=documents, embeddings=embeddings.tolist(), metadatas=metadatas, ids=ids)
    return _INDEX_PATH


def retrieve_best_match(text: str, label: str) -> Tuple[Optional[GroundedConcept], str, float]:
    if SentenceTransformer is not None:
        try:
            model = get_embedding_model()
            entries = _load_seed_entries()
            if entries:
                documents = [f"{entry.get('name', '')} {entry.get('description', '')}" for entry in entries]
                vectors = model.encode(documents, normalize_embeddings=True)
                query = model.encode([text], normalize_embeddings=True)[0]
                scores = vectors @ query
                best_index = int(scores.argmax())
                best_entry = entries[best_index]
                ontology = best_entry.get("ontology", "UNKNOWN")
                if ontology not in {"SNOMED", "ICD-10", "RxNorm", "UNKNOWN"}:
                    ontology = "UNKNOWN"
                return GroundedConcept(
                    ontology=ontology,
                    code=str(best_entry.get("code", "00000")),
                    name=str(best_entry.get("name", text)),
                ), "huggingface", max(0.0, float(scores[best_index]))
        except Exception:
            pass

    if chromadb is None or SentenceTransformer is None:
        return None, "fallback", 0.0

    if not os.path.exists(_INDEX_PATH):
        build_ontology_index()

    if not os.path.exists(_INDEX_PATH):
        return None, "fallback", 0.0

    try:
        client = chromadb.PersistentClient(path=_INDEX_PATH)
        collection = client.get_collection("ontology")
        model = SentenceTransformer("all-MiniLM-L6-v2")
        embedding = model.encode([text], convert_to_numpy=True)[0].tolist()
        results = collection.query(query_embeddings=[embedding], n_results=3)
        if not results.get("documents") or not results["documents"][0]:
            return None, "fallback", 0.0
        best_doc = results["documents"][0][0]
        best_meta = results["metadatas"][0][0]
        similarity = 0.0
        if results.get("distances") and results["distances"][0]:
            similarity = max(0.0, 1.0 - results["distances"][0][0])
        concept = GroundedConcept(
            ontology=best_meta.get("ontology", "UNKNOWN"),
            code=best_meta.get("code", "00000"),
            name=best_meta.get("name", text),
        )
        return concept, "rag", similarity
    except Exception:
        return None, "fallback", 0.0


def retrieve_best_matches(texts: list[str]) -> list[Tuple[Optional[GroundedConcept], str, float]]:
    """Ground a multiple entities with one cached model load and one batch encode."""
    if SentenceTransformer is None or not texts:
        return [(None, "fallback", 0.0) for _ in texts]
    try:
        entries = _load_seed_entries()
        if not entries:
            return [(None, "fallback", 0.0) for _ in texts]
        model = get_embedding_model()
        documents = [f"{entry.get('name', '')} {entry.get('description', '')}" for entry in entries]
        document_vectors = model.encode(documents, normalize_embeddings=True, show_progress_bar=False)
        query_vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        results = []
        for query_vector in query_vectors:
            scores = document_vectors @ query_vector
            best_entry = entries[int(scores.argmax())]
            ontology = best_entry.get("ontology", "UNKNOWN")
            if ontology not in {"SNOMED", "ICD-10", "RxNorm", "UNKNOWN"}:
                ontology = "UNKNOWN"
            results.append((GroundedConcept(
                ontology=ontology,
                code=str(best_entry.get("code", "00000")),
                name=str(best_entry.get("name", "")),
            ), "huggingface", max(0.0, float(scores.max()))))
        return results
    except Exception:
        return [(None, "fallback", 0.0) for _ in texts]
