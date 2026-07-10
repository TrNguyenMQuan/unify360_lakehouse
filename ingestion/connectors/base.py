# Base class
from __future__ import annotations
from abc import ABC, abstractmethod
import pandas as pd


class Connector(ABC):                      # ABC = Abstract Base Class
    def __init__(self, config: dict):
        self.config = config               # 1 row in sources.yml

    @abstractmethod
    def extract(self, since: str | None = None) -> pd.DataFrame:
        # Read data and return df
        # If since != None -> only select record > since (incremental)
        ...
