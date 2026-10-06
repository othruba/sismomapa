import os
from datetime import date, datetime, time, timedelta, timezone
from math import log, pi, radians, tan
from pathlib import Path
from time import perf_counter

import clickhouse_connect
import plotly.express as px
import streamlit as st


LIMITE_MAPA = 20_000
RAIZ_PROJETO = Path(__file__).resolve().parent


def carregar_env() -> None:
    arquivo = RAIZ_PROJETO / ".env"
    if not arquivo.exists():
        return

    for linha in arquivo.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue

        chave, valor = linha.split("=", 1)
        os.environ.setdefault(chave.strip(), valor.strip().strip("\"'"))


@st.cache_resource
def conectar_clickhouse():
    carregar_env()
    return clickhouse_connect.get_client(
        host=os.getenv("CLICKHOUSE_HOST", "localhost"),
        port=int(os.getenv("CLICKHOUSE_PORT", "8123")),
        username=os.getenv("CLICKHOUSE_USER", "default"),
        password=os.getenv("CLICKHOUSE_PASSWORD", ""),
        database="sismomapa",
    )


def consultar_eventos(data_inicial, data_final, magnitude, local):
    inicio = datetime.combine(data_inicial, time.min, tzinfo=timezone.utc)
    fim = datetime.combine(
        data_final + timedelta(days=1), time.min, tzinfo=timezone.utc
    )
    parametros = {
        "inicio": inicio,
        "fim": fim,
        "mag_min": magnitude[0],
        "mag_max": magnitude[1],
    }

    filtros = """
        time >= {inicio:DateTime64(3)}
        AND time < {fim:DateTime64(3)}
        AND mag >= {mag_min:Float32}
        AND mag <= {mag_max:Float32}
    """

    if local:
        filtros += " AND place ILIKE {local:String}"
        parametros["local"] = f"%{local}%"

    consulta_resumo = f"""
        SELECT
            count() AS total
        FROM terremotos
        WHERE {filtros}
    """
    consulta_eventos = f"""
        SELECT time, latitude, longitude, depth, mag, place
        FROM terremotos
        WHERE {filtros}
        ORDER BY mag DESC, time DESC
        LIMIT {LIMITE_MAPA}
    """

    client = conectar_clickhouse()
    inicio_consulta = perf_counter()
    resumo = client.query(consulta_resumo, parameters=parametros).first_row
    eventos = client.query_df(consulta_eventos, parameters=parametros)
    duracao = perf_counter() - inicio_consulta

    return {
        "eventos": eventos,
        "total": int(resumo[0]),
        "duracao": duracao,
        "busca_local": bool(local),
    }


def calcular_visao_mapa(eventos):
    coordenadas = eventos[["latitude", "longitude"]].dropna()
    lat_min = max(-85, coordenadas["latitude"].min())
    lat_max = min(85, coordenadas["latitude"].max())
    lon_min = coordenadas["longitude"].min()
    lon_max = coordenadas["longitude"].max()

    # Uma margem mínima evita um zoom excessivo quando todos os eventos estão
    # no mesmo ponto ou muito próximos entre si.
    margem_lat = max((lat_max - lat_min) * 0.15, 0.15)
    margem_lon = max((lon_max - lon_min) * 0.15, 0.15)
    sul = max(-85, lat_min - margem_lat)
    norte = min(85, lat_max + margem_lat)
    oeste = max(-180, lon_min - margem_lon)
    leste = min(180, lon_max + margem_lon)

    def latitude_mercator(latitude):
        return log(tan(pi / 4 + radians(latitude) / 2))

    fracao_lat = abs(latitude_mercator(norte) - latitude_mercator(sul)) / (2 * pi)
    fracao_lon = (leste - oeste) / 360
    zoom_lat = log(630 / (512 * fracao_lat), 2)
    zoom_lon = log(750 / (512 * fracao_lon), 2)

    return {
        "center": {"lat": (sul + norte) / 2, "lon": (oeste + leste) / 2},
        "zoom": max(0.7, min(10.5, zoom_lat, zoom_lon)),
    }


def criar_mapa(eventos, ajustar_aos_pontos=False):
    dados_mapa = eventos.copy()
    dados_mapa["tamanho_marcador"] = dados_mapa["mag"].clip(lower=0.5) ** 3
    opcoes_iniciais = {}
    if ajustar_aos_pontos:
        opcoes_iniciais = calcular_visao_mapa(dados_mapa)
    else:
        opcoes_iniciais = {"zoom": 0.7, "center": {"lat": 15, "lon": 0}}

    figura = px.scatter_map(
        dados_mapa,
        lat="latitude",
        lon="longitude",
        size="tamanho_marcador",
        color="depth",
        color_continuous_scale="Turbo",
        size_max=34,
        map_style="carto-positron",
        opacity=0.78,
        hover_name="place",
        hover_data={
            "time": "|%d/%m/%Y %H:%M UTC",
            "mag": ":.1f",
            "depth": ":.1f",
            "latitude": False,
            "longitude": False,
            "tamanho_marcador": False,
        },
        labels={
            "time": "Data",
            "mag": "Magnitude",
            "depth": "Profundidade (km)",
        },
        **opcoes_iniciais,
    )

    figura.update_layout(
        height=650,
        margin={"l": 0, "r": 0, "t": 10, "b": 0},
        coloraxis_colorbar={"title": "Profundidade<br>(km)"},
    )

    return figura


def criar_grafico_dispersao(eventos):
    dados_grafico = eventos.copy()
    dados_grafico["tamanho_marcador"] = dados_grafico["mag"].clip(lower=0.1) ** 5

    figura = px.scatter(
        dados_grafico,
        x="time",
        y="depth",
        size="tamanho_marcador",
        size_max=48,
        opacity=0.7,
        hover_name="place",
        hover_data={
            "time": "|%d/%m/%Y %H:%M UTC",
            "mag": ":.1f",
            "depth": ":.1f",
            "latitude": ":.3f",
            "longitude": ":.3f",
            "tamanho_marcador": False,
        },
        labels={
            "time": "Data",
            "depth": "Profundidade (km)",
            "mag": "Magnitude",
        },
    )
    figura.update_layout(
        height=440,
        margin={"l": 0, "r": 0, "t": 10, "b": 0},
        showlegend=False,
    )

    figura.update_yaxes(
        range=[
            dados_grafico["depth"].max(),
            dados_grafico["depth"].min()
        ])
    return figura


st.set_page_config(page_title="SismoMapa", page_icon="🌎", layout="wide")

st.title("🌎 SismoMapa")
st.caption("Explore os terremotos armazenados no ClickHouse.")

with st.sidebar:
    st.header("Filtros")
    with st.form("filtros"):
        data_inicial = st.date_input(
            "Data inicial", value=date(2010, 1, 1), max_value=date.today()
        )
        data_final = st.date_input(
            "Data final", value=date.today(), max_value=date.today()
        )
        magnitude = st.slider(
            "Magnitude", min_value=0.0, max_value=10.0, value=(2.0, 10.0), step=0.1
        )
        local = st.text_input("Local", placeholder="Ex.: Brazil, Japan")
        aplicar = st.form_submit_button(
            "Aplicar filtros", type="primary", width="stretch"
        )

if aplicar:
    if data_inicial > data_final:
        st.error("A data inicial deve ser anterior ou igual à data final.")
        st.stop()

    try:
        st.session_state["resultado"] = consultar_eventos(
            data_inicial, data_final, magnitude, local.strip()
        )
    except Exception as erro:
        st.error(f"Não foi possível consultar o ClickHouse: {erro}")
        st.stop()

resultado = st.session_state.get("resultado")

if resultado is None:
    st.info("Escolha os filtros na barra lateral e clique em **Aplicar filtros**.")
    st.stop()

eventos = resultado["eventos"]
total = resultado["total"]

col_total, col_exibidos, col_tempo = st.columns(3)
col_total.metric("Eventos encontrados", f"{total:,}".replace(",", "."))
col_exibidos.metric("Eventos no mapa", f"{len(eventos):,}".replace(",", "."))
col_tempo.metric("Tempo das consultas", f"{resultado['duracao']:.3f} s")

if eventos.empty:
    st.info("Nenhum evento encontrado para os filtros selecionados.")
    st.stop()

if total > len(eventos):
    st.caption(
        f"O mapa mostra os {LIMITE_MAPA:,} eventos de maior magnitude.".replace(",", ".")
    )

st.plotly_chart(
    criar_mapa(eventos, ajustar_aos_pontos=resultado["busca_local"]), width="stretch"
)

st.subheader("Eventos sísmicos por data e profundidade")
st.plotly_chart(criar_grafico_dispersao(eventos), width="stretch")
