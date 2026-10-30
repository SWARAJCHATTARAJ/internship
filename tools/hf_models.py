"""Lazy Hugging Face model loaders shared by the specialist agents."""
from __future__ import annotations

from functools import lru_cache
import os

import torch


NER_MODEL = "d4data/biomedical-ner-all"
RELATION_MODEL = "wesin/pubmedbert-relation-extraction"
EMBEDDING_MODEL = "NeuML/biomedbert-base-embeddings"


def get_torch_device() -> str:
    requested = os.getenv("MODEL_DEVICE", "auto").lower()
    if requested == "cpu":
        return "cpu"
    if requested == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("MODEL_DEVICE=cuda was requested, but CUDA is unavailable")
    return "cuda" if torch.cuda.is_available() else "cpu"


@lru_cache(maxsize=1)
def get_ner_pipeline():
    from transformers import pipeline

    return pipeline(
        "token-classification",
        model=NER_MODEL,
        aggregation_strategy="simple",
        device=0 if get_torch_device() == "cuda" else -1,
    )


@lru_cache(maxsize=1)
def get_relation_model():
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(RELATION_MODEL)
    special_tokens = {"additional_special_tokens": ["[E1]", "[/E1]", "[E2]", "[/E2]"]}
    tokenizer.add_special_tokens(special_tokens)
    model = AutoModelForSequenceClassification.from_pretrained(RELATION_MODEL)
    model.resize_token_embeddings(len(tokenizer))
    model.to(get_torch_device())
    model.eval()
    return tokenizer, model


@lru_cache(maxsize=1)
def get_embedding_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(EMBEDDING_MODEL, device=get_torch_device())