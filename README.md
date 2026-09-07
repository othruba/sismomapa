# SismoMapa

Aplicação local para consultar e visualizar em um mapa os dados de terremotos do
USGS armazenados no ClickHouse.

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

Instale as dependências e execute as três etapas de extração, transformação e
carga:

```bash
uv sync
uv run python etl/01_extract.py
uv run python etl/02_transform.py
uv run python etl/03_load.py
```

O arquivo `etl/03_load.py` carrega `data/terremotos.parquet` na tabela
`sismomapa.terremotos` e usa as variáveis definidas em `.env`.

## Executar a aplicação

Com o ClickHouse em execução e os dados carregados:

```bash
uv run streamlit run app.py
```

A aplicação fica disponível em `http://localhost:8501`. Na barra lateral é
possível filtrar por período, intervalo de magnitude e texto do local. Os filtros
são enviados ao ClickHouse somente ao clicar em **Aplicar filtros**; o Pandas
recebe apenas os resultados já filtrados. O mapa exibe no máximo 20.000 eventos,
priorizando os de maior magnitude.
