# RestConnector: Read stripe json
from __future__ import annotations
import json
import pandas as pd
from ingestion.connectors.base import Connector

class RestConnector(Connector):
    def extract(self, since=None) -> pd.DataFrame:
        path = self.config["path"]
        with open(path) as file:
            records = json.load(file) # -> list[dict]

        # json_normalize: {'metadata': {'country': 'VN'}} -> column metadata.country
        df = pd.json_normalize(records)
        return df.astype(str)   # bronze raw landing
