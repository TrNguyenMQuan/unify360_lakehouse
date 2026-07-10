# MongoConnector: read collection Mongo
from __future__ import annotations
from pymongo import MongoClient
import pandas as pd
from ingestion.connectors.base import Connector
from ingestion.config import MONGO

class MongoConnector(Connector):
    def extract(self, since=None) -> pd.DataFrame:
        db_name = self.config["database"]
        coll_name = self.config["collection"]

        query_filter = {}
        if since is not None:
            wm = self.config["watermark"]
            since_dt = pd.to_datetime(since).to_pydatetime()
            query_filter = {wm: {"$gt": since_dt}}

        with MongoClient(**MONGO) as client:
            docs = list(client[db_name][coll_name].find(query_filter, {"_id": 0}))

        # json_normalize: {'properties' : {...} and 'context': {...}}
        df = pd.json_normalize(docs)
        return df.astype(str)