import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Tuple
from .base import BaseExtractor

class Form13Extractor(BaseExtractor):
    def parse(self, file_path: Path) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        df = pd.read_csv(
             file_path,
             dtype={
                'source': 'string',
                'managerCik': 'int64',
                'managerAddress': 'string',
                'managerName': 'string',
                'cusip6': 'string',
                'cusip': 'string',
                'companyName': 'string',
                'value': 'float64',
                'shares': 'int64'
             },
             parse_dates=['reportCalendarOrQuarter']
        )

        managers_df = df[['managerCik', 'managerName', 'managerAddress']].drop_duplicates(subset=['managerCik'])
        managers_df = managers_df.rename(columns={
            'managerCik': 'manager_cik',
            'managerName': 'name',
            'managerAddress': 'address'
        })

        holdings_df = df[[
            'managerCik', 'reportCalendarOrQuarter', 'cusip6',
            'cusip', 'companyName', 'value', 'shares', 'source'
        ]].copy()

        holdings_df = holdings_df.rename(columns={
            'managerCik': 'manager_cik',
            'reportCalendarOrQuarter': 'report_date',
            'companyName': 'company_name'
        })

        holdings_df['report_date'] = holdings_df['report_date'].dt.date

        return (
            managers_df.to_dict(orient='records'),
            holdings_df.to_dict(orient='records')
        )