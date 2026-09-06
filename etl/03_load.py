import os
from pathlib import Path

import clickhouse_connect
import pandas as pd


def carregar_env(caminho):
    if not caminho.exists():
        return

    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()

        if not linha or linha.startswith("#") or "=" not in linha:
            continue

        chave, valor = linha.split("=", 1)
        os.environ.setdefault(chave.strip(), valor.strip().strip("\"'"))


raiz_projeto = Path(__file__).resolve().parent.parent
carregar_env(raiz_projeto / ".env")

arquivo = raiz_projeto / "data" / "terremotos.parquet"
database = "sismomapa"
tabela = "terremotos"

df = pd.read_parquet(arquivo)

client = clickhouse_connect.get_client(
    host="localhost",
    port=8123,
    username="default",
    password=os.getenv("CLICKHOUSE_PASSWORD", ""),
)

client.command(f"CREATE DATABASE IF NOT EXISTS {database}")

client.command(f"DROP TABLE IF EXISTS {database}.{tabela}")

client.command(f"""
    CREATE TABLE IF NOT EXISTS {database}.{tabela}
    (
        id String,
        time DateTime64(3, 'UTC'),
        latitude Float64,
        longitude Float64,
        depth Float32,
        mag Float32,
        place String
    )
    ENGINE = MergeTree
    PARTITION BY toYear(time)
    ORDER BY (time, latitude, longitude, id)
""")

client.insert_df(tabela, df, database=database)

print(client.command(f"SELECT count() FROM {database}.{tabela}"))

client.close()
