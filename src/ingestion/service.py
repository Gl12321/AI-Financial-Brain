from typing import Dict
from pathlib import Path
from src.core.logger import setup_logger

logger = setup_logger("IngestionService")


class IngestionService:
    def __init__(self, repository, extractors: Dict, summary_engine=None, embedder_processor=None):
        self.repository = repository
        self.extractors = extractors
        self.summary_engine = summary_engine
        self.embedder_processor = embedder_processor

    async def process_folders(self, folder_path: Path):
        await self.process_form10_chunks(folder_path)
        await self.process_form10(folder_path)
        await self.process_form13(folder_path)

    async def process_form10_chunks(self, folder_path: Path):
        target = folder_path / "form10"
        for file_path in target.glob('*.json'):
            await self._run_extraction(file_path, "10k_chunks")

    async def process_form10(self, folder_path: Path):
        target = folder_path / "form10"
        for file_path in target.glob('*.json'):
            await self._run_extraction(file_path, "10k_full")

    async def process_form13(self, folder_path: Path):
        target = folder_path / "form13"
        for file_path in target.glob("*.csv"):
            await self._run_extraction(file_path, '13f')

    async def _run_extraction(self, file_path: Path, doc_type: str):
        extractor = self.extractors.get(doc_type)

        try:
            data = extractor.parse(file_path)

            if doc_type == "10k_chunks":
                await self.repository.save_10k_chunks(data)
            elif doc_type == "10k_full":
                await self.repository.save_form10_full(data)
            elif doc_type == "13f":
                await self.repository.save_13f_holdings(data)

            logger.info(f"Successfully processed {file_path.name}")
        except Exception as e:
            logger.error(f"Failed to process {file_path.name}: {e}")

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

    async def run_chunks_embedding(self, batch_size=10):
        await self.embedder_processor.run_chunks_embedding(batch_size)

    async def run_embedding_form10(self, batch_size=5):
        await self.embedder_processor.run_form10_embedding(batch_size)