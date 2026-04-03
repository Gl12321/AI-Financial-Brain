import os
from sentence_transformers import SentenceTransformer

from src.core.config import get_settings
from src.core.logger import setup_logger

logger = setup_logger("EMBEDDER")
settings = get_settings()


class Embedder:
    def __init__(self):
        embedder_config = settings.MODELS["embedder"]
        model_name = embedder_config["repo_id"]
        _device = embedder_config["device"]
        cache_path = embedder_config["cache_path"]
        dimension = embedder_config["dimension"]

        if not cache_path.exists():
            os.mkdir(cache_path)

        self.model = SentenceTransformer(
            model_name,
            device = _device,
            cache_folder = cache_path,
            dimension = dimension
        )
        logger.info("Model loaded")

    def get_embeddings(self, texts):
        return self.model.encode(
            texts,
            show_progress_bar=False
        ).tolist()