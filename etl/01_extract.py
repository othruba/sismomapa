from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
import shutil


BASE_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"

PASTA_ETL = Path(__file__).resolve().parent
RAIZ_PROJETO = PASTA_ETL.parent

PASTA = RAIZ_PROJETO / "data"
ARQUIVO_FINAL = PASTA / "terremotos.csv"

LIMITE = 20_000
arquivos_baixados = []

PASTA.mkdir(exist_ok=True)

for ano in range(2010, 2027):
    inicio = f"{ano}-01-01 00:00:00"
    fim = (
        "2026-09-01 23:59:59"
        if ano == 2026
        else f"{ano}-12-31 23:59:59"
    )

    offset = 1
    lote = 1

    print(f"\nBaixando dados de {ano}...")

    while True:
        parametros = {
            "format": "csv",
            "starttime": inicio,
            "endtime": fim,
            "minmagnitude": 2,
            "orderby": "time-asc",
            "limit": LIMITE,
            "offset": offset,
        }

        url = f"{BASE_URL}?{urlencode(parametros)}"
        arquivo = PASTA / f"terremotos_{ano}_lote_{lote:03d}.csv"

        print(f"  Lote {lote} (offset {offset})...")

        with urlopen(url, timeout=300) as resposta:
            arquivo.write_bytes(resposta.read())

        # Subtrai uma linha, que corresponde ao cabeçalho CSV.
        with arquivo.open(encoding="utf-8") as f:
            quantidade = sum(1 for _ in f) - 1

        if quantidade <= 0:
            arquivo.unlink()
            break

        arquivos_baixados.append(arquivo)
        print(f"    {quantidade} registros")

        if quantidade < LIMITE:
            break

        offset += LIMITE
        lote += 1


print("\nJuntando arquivos...")

with ARQUIVO_FINAL.open("w", encoding="utf-8", newline="") as destino:
    for indice, arquivo in enumerate(arquivos_baixados):
        with arquivo.open("r", encoding="utf-8", newline="") as origem:
            if indice > 0:
                next(origem)

            shutil.copyfileobj(origem, destino)

print("\nLimpando arquivos temporários...")

arquivos_removidos = 0
for arquivo in arquivos_baixados:
    if arquivo != ARQUIVO_FINAL and arquivo.exists():
        arquivo.unlink()
        arquivos_removidos += 1

print(f"Arquivos temporários removidos: {arquivos_removidos}")
print(f"Concluído: {ARQUIVO_FINAL}")
