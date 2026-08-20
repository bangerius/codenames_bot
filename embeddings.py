from __future__ import annotations

import os
from typing import Any, cast

import fasttext
import gensim.downloader as api
import numpy as np
from gensim.models.keyedvectors import KeyedVectors

LANGUAGE_MODELS = {
    "en": "fasttext-wiki-news-subwords-300",
    "sv": "cc.sv.300.bin",
}


def default_model_name_for_language(lang: str) -> str:
    return LANGUAGE_MODELS.get(lang.lower(), LANGUAGE_MODELS["en"])


class EmbeddingModel:
    def __init__(self, model: Any, lang: str):
        self.model = model
        self.lang = lang.lower()

    def get_vector(self, word: str) -> np.ndarray:
        if isinstance(self.model, KeyedVectors):
            return np.asarray(self.model.get_vector(word), dtype=float)
        return np.asarray(self.model.get_word_vector(word), dtype=float)

    def cosine_similarity(self, vector_a: np.ndarray, vector_b: np.ndarray) -> float:
        left = np.asarray(vector_a, dtype=float)
        right = np.asarray(vector_b, dtype=float)
        denom = np.linalg.norm(left) * np.linalg.norm(right)
        if np.isclose(denom, 0.0):
            return 0.0
        return float(np.dot(left, right) / denom)

    def cosine_similarities(self, vector: np.ndarray, vectors: list[np.ndarray]) -> list[float]:
        return [self.cosine_similarity(vector, candidate) for candidate in vectors]

    def _as_vector(self, value: Any) -> np.ndarray:
        if value is None:
            return np.zeros(1, dtype=float)
        if isinstance(value, str):
            return self.get_vector(value)
        if isinstance(value, (list, tuple)):
            if value and all(isinstance(item, str) for item in value):
                return self._combine(value)
            return np.asarray(value, dtype=float)
        if isinstance(value, np.ndarray):
            return value.astype(float)
        return np.asarray(value, dtype=float)

    def _combine(self, values: list[Any]) -> np.ndarray:
        vectors = [self._as_vector(value) for value in values]
        if not vectors:
            raise ValueError("No vectors provided for combination.")
        return sum(vectors) / len(vectors)

    def most_similar(self, positive: Any, negative: Any = None, topn: int = 10):
        if isinstance(self.model, KeyedVectors):
            return self.model.most_similar(positive=positive, negative=negative, topn=topn)

        positive_vector = self._as_vector(positive)
        negative_vector = self._as_vector(negative) if negative is not None else np.zeros_like(positive_vector)
        combined_vector = positive_vector - negative_vector

        scored = []
        for word in self.model.get_words():
            candidate_vector = self.get_vector(word)
            score = self.cosine_similarity(combined_vector, candidate_vector)
            scored.append((word, float(score)))

        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:topn]


def load_embedding_model(lang: str = "en", model_name: str | None = None) -> EmbeddingModel:
    language = lang.lower()
    resolved_name = model_name or default_model_name_for_language(language)

    if language == "sv":
        sv_model_path = "cc.sv.300.bin"
        if not os.path.exists(sv_model_path):
            fasttext.util.download_model("sv", if_exists="ignore")
            if not os.path.exists(sv_model_path):
                raise FileNotFoundError("Swedish model not found; expected cc.sv.300.bin after download.")
        return EmbeddingModel(fasttext.load_model(sv_model_path), language)

    binary_path = f"{resolved_name}.bin"
    if not os.path.exists(binary_path):
        model = cast(KeyedVectors, api.load(resolved_name))
        model.sort_by_descending_frequency()
        model.save_word2vec_format(binary_path, binary=True)
        return EmbeddingModel(model, language)

    return EmbeddingModel(KeyedVectors.load_word2vec_format(binary_path, binary=True), language)
