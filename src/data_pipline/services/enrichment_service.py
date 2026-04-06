from pathlib import Path

from src.core.logger import setup_logger

logger = setup_logger("ENRICHER_SERVICE")


class EnrichmentService:
    def __init__(self, writer_repository, reader_repository, summary_engine, embedder_processor):
        self.writer_repository = writer_repository
        self.reader_repository = reader_repository
        self.summary_engine = summary_engine
        self.embedder_processor = embedder_processor

    async def run_chunks_embedding(self):
        while True:
            chunks_to_embedder = await self.reader_repository.get_chunks_without_embeddings(limit=100)
            if not chunks_to_embedder:
                logger.info("No chunks pending embedding")
                break

            batch_size = 5
            for i in range(0, len(chunks_to_embedder), batch_size):
                batch = chunks_to_embedder[i: i+batch_size]
                embeddings_with_ids = await self.embedder_processor.run_chunks_embedding(batch, len(batch))

                await self.writer_repository.save_embeddings_for_chunks(embeddings_with_ids)

    async def run_embedding_form10(self, batch_size=5):
        pass

    async def summarize_pending_forms(self, data_folder: Path):
        forms = await self.repository.get_forms_without_summary()
        if not forms:
            logger.info("No forms pending summarization")
            return

        extractor = self.extractors.get("10k_full")

        for form in forms:
            form_id = form['form_id']
            file_path = data_folder / "form10" / f"{form_id}.json"

            data = extractor.parse(file_path)
            full_text = data["full_text"]
            summary = self.summary_engine.summarize(full_text)
            await self.repository.update_form_summary(form_id, summary)
            logger.info(f"Summary saved for {form_id}")

        logger.info(f"Summarized {len(forms)} forms")
