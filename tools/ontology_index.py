import json
import os
from typing import Optional, Tuple, cast, Literal

from schemas.core import GroundedConcept

try:
    import chromadb
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover
    chromadb = None
    SentenceTransformer = None


_DATA_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'ontology_seed.json')
_INDEX_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'ontology_index')


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
        docs = results.get("documents")
        metas = results.get("metadatas")
        dists = results.get("distances")
        if not docs or not docs[0] or not metas or not metas[0]:
            return None, "fallback", 0.0
        best_doc = docs[0][0]
        best_meta = metas[0][0]
        similarity = 0.0
        if dists and dists[0]:
            similarity = max(0.0, 1.0 - float(dists[0][0]))
        if isinstance(best_meta, dict):
            ont_raw = str(best_meta.get("ontology", "UNKNOWN"))
            ont_val = cast(Literal["SNOMED", "ICD-10", "RxNorm", "UNKNOWN"], ont_raw if ont_raw in {"SNOMED", "ICD-10", "RxNorm", "UNKNOWN"} else "UNKNOWN")
            concept = GroundedConcept(
                ontology=ont_val,
                code=str(best_meta.get("code", "00000")),
                name=str(best_meta.get("name", text)),
            )
            return concept, "rag", similarity
        return None, "fallback", 0.0
    except Exception:
        return None, "fallback", 0.0
