import pandas as pd

df = pd.read_csv("data/terremotos.csv")
selecao = ["id", "time", "latitude", "longitude", "depth", "mag", "place"]
df = df[selecao].copy()
df["time"] = pd.to_datetime(df["time"], utc=True)

df.to_parquet("data/terremotos.parquet")
