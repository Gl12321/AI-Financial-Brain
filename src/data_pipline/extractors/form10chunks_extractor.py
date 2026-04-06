import json
from pathlib import Path
from typing import List, Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .base import BaseExtractor
from src.core.logger import setup_logger

logger = setup_logger("Form10ChunksExtractor")


class Form10ChunksExtractor(BaseExtractor):
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size = 2000,
                chunk_overlap  = 200,
                length_function = len,
                is_separator_regex = False,
            )

        self.max_chunks_from_item = 20

    def parse(self, file_path: Path) -> List[Dict[str, Any]]:
        chunks_with_metadata = []
        path_str = str(file_path)

        file_as_object = json.loads(file_path.read_text(encoding='utf-8'))

        for item in ['item1', 'item1a', 'item7', 'item7a']:
            item_text = file_as_object.get(item, "")
            if not item_text:
                continue

            item_text_chunks = self.text_splitter.split_text(item_text)
            chunk_inc_id = 0

            for chunk in item_text_chunks[:self.max_chunks_from_item]:
                form_id = path_str[path_str.rindex('/') + 1: path_str.rindex('.')]

                chunks_with_metadata.append({
                    'text': chunk,
                    'item': item,
                    'formId': f'{form_id}',
                    'chunkId': f'{form_id}-{item}-chunk{chunk_inc_id:04d}',
                    'names': file_as_object['names'],
                    'cik': int(file_as_object['cik']),
                    'cusip6': file_as_object['cusip6'],
                    'source': file_as_object['source'],
                })
                chunk_inc_id += 1

        logger.info(f"{file_path.name} was extracted with {len(chunks_with_metadata)} chunks")
        return chunks_with_metadata