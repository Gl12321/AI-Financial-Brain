import pandas as pd
from pathlib import Path
from typing import List, Dict, Any
from .base import BaseExtractor

class Form13Extractor(BaseExtractor):
    def parse(self, file_path: Path) -> List[Dict[str, Any]]:
        df = pd.read_csv(file_path)

        return df.to_dict(orient='records')