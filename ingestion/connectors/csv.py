# CsvConnector - read data from csv
from __future__ import annotations
import pandas as pd
from ingestion.connectors.base import Connector

# Subclass
class CsvConnector(Connector):
    def extract(self, since=None): # override
        path = self.config["path"]
        df = pd.read_csv(path, dtype=str) # bronze store raw data
        return df