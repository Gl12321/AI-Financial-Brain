import json
from pathlib import Path
from typing import Any, Dict

from src.data_pipline.extractors.base import BaseExtractor
from src.core.logger import setup_logger
from src.core.config import get_settings

logger = setup_logger("FORM10_EXTRACTOR")
settings = get_settings()


class Form10Extractor(BaseExtractor):
    def parse(self, file_path: Path) -> Dict[str, Any]:
        text_storage_path = settings.DATA_RAW_DIR / "form10_text"
        text_storage_path.mkdir(parents=True, exist_ok=True)

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                file_as_object = json.load(f)

            file_name = file_path.name
            form_id = file_name[:file_name.rindex('.')]
            names = file_as_object.get('names', ['Unknown'])

            full_text = f"About {names[0]}...\n"
            for item in ['item1', 'item1a', 'item7', 'item7a']:
                if item in file_as_object:
                    full_text += f"{file_as_object[item]}"

            text_file = text_storage_path / f"{form_id}.txt"
            with open(text_file, 'w', encoding='utf-8') as f:
                f.write(full_text)

            logger.info(f"{file_name} form10 extracted")

            return {
                "formId": form_id,
                "names": names,
                "cik": int(file_as_object['cik']),
                "cusip6": file_as_object.get('cusip6'),
                "cusip": file_as_object.get('cusip'),
                "source": file_as_object.get('source'),
                "summary": None
            }

        except Exception as e:
            logger.error(f"{e}")
