from src.core.logger import setup_logger
from src.infrastructure.llm.embedder import Embedder

logger = setup_logger("INDEXER_PROCESSOR")


class IndexerProcessor:
    def __init__(self, repository):
        self.repo = repository
        self.embedder = Embedder()

    def run_chunks_indexing(self, batch_size=100):

        logger.info("Starting chunks indexing process")

        while True:
            records = self.repo.get_unindexed_chunks(limit=batch_size)
            if not records:
                logger.info("All chunks are already indexed")
                break

            ids = [r['chunk_id'] for r in records]
            texts = [r['chunk_text'] for r in records]

            vectors = self.embedder.get_embeddings(texts)

            upload_data = list(zip(ids, vectors))
            self.repo.save_chunk_embeddings(upload_data)

            logger.info(f"Indexed {len(ids)} chunks")