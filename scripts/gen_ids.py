"""Regenerate product_id column in products.csv using deterministic SHA-1 hashes."""
import pandas as pd
from etl.id_utils import make_product_id

df = pd.read_csv("data/samples/products.csv")
ids = []
for _, r in df.iterrows():
    pid = make_product_id(
        str(r["brand"]), str(r["line"]), str(r["name"]),
        int(r["size_ml"]), str(r["concentration"])
    )
    ids.append(pid)
df["product_id"] = ids
# reorder columns with product_id first
cols = ["product_id","brand","line","name","size_ml","concentration","notes"]
df = df[cols]
df.to_csv("data/samples/products.csv", index=False)
print("Wrote IDs into data/samples/products.csv")
