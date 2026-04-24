import logging
from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _load_model(model_name: str, device: str) -> "SentenceTransformer":
    from sentence_transformers import SentenceTransformer
    logger.info("Loading embedding model: %s on %s", model_name, device)
    return SentenceTransformer(model_name, device=device)


class Embedder:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", device: str = "cpu") -> None:
        self._model_name = model_name
        self._device = device

    @property
    def model(self) -> "SentenceTransformer":
        return _load_model(self._model_name, self._device)

    def embed(self, texts: list[str], batch_size: int = 64) -> list[list[float]]:
        if not texts:
            return []
        vectors = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return vectors.tolist()

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]

    @property
    def dimension(self) -> int:
        return self.model.get_sentence_embedding_dimension()
