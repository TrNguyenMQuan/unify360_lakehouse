# JdbcConnector: querry table from postgres
from __future__ import annotations
import psycopg
from psycopg import sql
import pandas as pd
from ingestion.connectors.base import Connector
from ingestion.config import POSTGRES

class JdbcConnector(Connector):
    def extract(self, since=None) -> pd.DataFrame:
        table = self.config["table"]
        query = sql.SQL("SELECT * FROM {}").format(
            sql.Identifier(*table.split("."))
        )
        params = []
        if since is not None:
            wm = self.config["watermark"]
            query = sql.SQL("{} WHERE {} > %s").format(query, sql.Identifier(wm))
            params = [since]

        with psycopg.connect(**POSTGRES) as conn, conn.cursor() as cur:
            cur.execute(query, params)
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()

        return pd.DataFrame(rows, columns=cols).astype(str)

