from typing import Dict
from pathlib import Path
from src.core.logger import setup_logger

logger = setup_logger("IngestionService")


class IngestionService:
    def __init__(self, repository, extractors: Dict):
        self.repository = repository
        self.extractors = extractors

    async def process_folders(self, folder_path: Path):
        await self.process_form10(folder_path)
        await self.process_form10_chunks(folder_path)
        await self.process_form13(folder_path)

    async def process_form10_chunks(self, folder_path: Path):
        target = folder_path / "form10"
        for file_path in target.glob('*.json'):
            await self._run_extraction(file_path, "10k_chunks")

    async def process_form10(self, folder_path: Path):
        target = folder_path / "form10"
        for file_path in target.glob('*.json'):
            await self._run_extraction(file_path, "10k_companies")

    async def process_form13(self, folder_path: Path):
        target = folder_path / "form13"
        for file_path in target.glob("*.csv"):
            await self._run_extraction(file_path, '13f_managers_holdings')

    async def _run_extraction(self, file_path: Path, doc_type: str):
        extractor = self.extractors.get(doc_type)

        try:
            data = extractor.parse(file_path)

            if doc_type == "10k_chunks":
                await self.repository.save_10k_chunks(data, batch_size=500)
            elif doc_type == "10k_companies":
                await self.repository.save_form10company(data)
            elif doc_type == "13f_managers_holdings":
                await self.repository.save_13f_holding_managers(data, batch_size=1000)

            logger.info(f"Successfully processed {file_path.name}")
        except Exception as e:
            logger.error(f"Failed to process {file_path.name}: {e}")
