# Sismomapa

Projeto de ETL para dados de terremotos do USGS, com carga em ClickHouse.

## Requisitos

- Python 3.12
- uv
- Docker com Docker Compose

## Subir o ClickHouse

Se o arquivo `.env` ainda não existir, crie a partir do exemplo:

```bash
cp .env.example .env
```

Se já existir um container manual com o mesmo nome, remova-o antes:

```bash
docker stop clickhouse-server
docker rm clickhouse-server
```

```bash
docker compose up -d
```

Verifique se o banco respondeu:

```bash
curl "http://localhost:8123/?password=clickhouse&query=SELECT%201"
```

## Executar o ETL

```bash
uv run python etl/01_extract.py
uv run python etl/02_transform.py
uv run python etl/03_load.py
```

O script de carga usa as variáveis definidas em `.env`.
