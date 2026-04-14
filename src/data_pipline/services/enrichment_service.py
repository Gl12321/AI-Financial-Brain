from pathlib import Path
import csv

from src.core.logger import setup_logger
from src.core.config import get_settings

settings = get_settings()
logger = setup_logger("ENRICHER_SERVICE")


class EnrichmentService:
    def __init__(self, writer_repository, reader_repository, summary_engine, embedder_processor):
        self.writer_repository = writer_repository
        self.reader_repository = reader_repository
        self.summary_engine = summary_engine
        self.embedder_processor = embedder_processor
        self.settings = settings

    async def run_chunks_embedding(self):
        while True:
            chunks_to_embedder = await self.reader_repository.get_chunks_without_embeddings(limit=100)
            if not chunks_to_embedder:
                logger.info("No chunks pending embedding")
                break

            batch_size = 5
            for i in range(0, len(chunks_to_embedder), batch_size):
                batch = chunks_to_embedder[i: i+batch_size]
                embeddings_with_ids = await self.embedder_processor.run_chunks_embedding(batch)

                await self.writer_repository.save_embeddings_for_chunks(embeddings_with_ids)

    async def run_embedding_form10(self, batch_size=10):
        while True:
            forms_to_embed = await self.reader_repository.get_form10_without_embeddings(limit=100)
            if not forms_to_embed:
                logger.info("No forms pending embedding")
                break

            for i in range(0, len(forms_to_embed), batch_size):
                batch = forms_to_embed[i:i + batch_size]
                embeddings_with_ids = await self.embedder_processor.run_form10_embedding(batch)

                await self.writer_repository.save_form10_embeddings(embeddings_with_ids)

    async def add_summaries(self, batch_size=100):
        summaries_file = self.settings.DATA_RAW_DIR / "form10_summaries" / "summaries.csv"

        if not summaries_file.exists():
            logger.error(f"Summaries file not found: {summaries_file}")
            return

        logger.info(f"Loading summaries from {summaries_file}")

        summaries = []
        with open(summaries_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                summaries.append({
                    "formId": row["formId"],
                    "summary": row["summary"]
                })


        await self.writer_repository.save_summaries(summaries, batch_size=batch_size)
        logger.info("Summaries saved successfully")



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

    async def run_item_aggregation(self, batch_size: int = 1000):
        filled_count = await self.writer_repository.fill_chunk_item_ids()
        if filled_count > 0:
            logger.info(f"Filled {filled_count} chunks with item_id")
        else:
            logger.info("No chunks needed item_id update")

        offset = 0
        total_aggregated = 0
        total_skipped = 0

        while True:
            grouped = await self.reader_repository.get_chunk_embeddings_grouped(limit=batch_size, offset=offset)
            if not grouped:
                break

            items_to_save = []
            for item_id, embeddings_list in grouped:
                aggregated = self.embedder_processor.aggregate_embeddings(embeddings_list)
                if aggregated:
                    items_to_save.append({"item_id": item_id, "embeddings": aggregated})
                    total_aggregated += 1
                else:
                    total_skipped += 1

            if items_to_save:
                await self.writer_repository.save_item_embeddings_batch(items_to_save)

            offset += batch_size

        if total_skipped > 0:
            logger.info(f"Aggregated {total_aggregated} items, skipped {total_skipped}")
        else:
            logger.info(f"Aggregated {total_aggregated} items")
