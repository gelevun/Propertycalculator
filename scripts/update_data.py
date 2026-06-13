import json
import os
from datetime import datetime

import pandas as pd
import yfinance as yf

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE, "data")


def load_json(name):
    path = os.path.join(DATA_DIR, name)
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return json.load(f)


def save_json(name, data):
    path = os.path.join(DATA_DIR, name)
    with open(path, "w") as f:
        json.dump(data, f)


def today():
    return datetime.now().strftime("%Y-%m-%d")


def fetch_yf(symbol):
    try:
        df = yf.download(symbol, period="5y", interval="1mo", progress=False, auto_adjust=True)
        if df.empty:
            return None
        df = df.reset_index()
        df["date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None).dt.strftime("%Y-%m-%d")
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [" ".join(c).strip() if isinstance(c, tuple) else c for c in df.columns]
        return df
    except Exception:
        return None


def merge_series(existing, new_rows, fields):
    seen = {r["date"]: r for r in existing}
    for row in new_rows:
        d = row.get("date")
        if d not in seen:
            seen[d] = {}
        for f in fields:
            if f in row and row[f] is not None:
                try:
                    seen[d][f] = float(row[f])
                except Exception:
                    pass
        seen[d]["date"] = d
    return sorted(seen.values(), key=lambda x: x["date"])


def update_fx():
    existing = load_json("fx.json")
    usd = fetch_yf("USDTRY=X")
    eur = fetch_yf("EURTRY=X")
    if usd is None or eur is None:
        return
    merged = {}
    for _, row in usd.iterrows():
        d = row["date"]
        merged[d] = {"date": d, "usd_try": float(row.get("Close USDTRY=X", row.get("Close", 0)))}
    for _, row in eur.iterrows():
        d = row["date"]
        if d not in merged:
            merged[d] = {"date": d}
        merged[d]["eur_try"] = float(row.get("Close EURTRY=X", row.get("Close", 0)))
    new_rows = list(merged.values())
    save_json("fx.json", merge_series(existing, new_rows, ["usd_try", "eur_try"]))


def update_gold():
    existing = load_json("gold.json")
    df = fetch_yf("XAUTRYG=X")
    if df is None:
        return
    rows = [{"date": row["date"], "price_try": float(row.get("Close XAUTRYG=X", row.get("Close", 0)))} for _, row in df.iterrows()]
    save_json("gold.json", merge_series(existing, rows, ["price_try"]))


def update_bist():
    existing = load_json("bist.json")
    bist = fetch_yf("XU100.IS")
    gyo = fetch_yf("XGYO.IS")
    merged = {}
    if bist is not None:
        for _, row in bist.iterrows():
            d = row["date"]
            merged[d] = {"date": d, "bist100": float(row.get("Close XU100.IS", row.get("Close", 0)))}
    if gyo is not None:
        for _, row in gyo.iterrows():
            d = row["date"]
            if d not in merged:
                merged[d] = {"date": d}
            merged[d]["gyox"] = float(row.get("Close XGYO.IS", row.get("Close", 0)))
    if not merged:
        return
    rows = list(merged.values())
    save_json("bist.json", merge_series(existing, rows, ["bist100", "gyox"]))


if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)
    update_fx()
    update_gold()
    update_bist()
    print("Data update attempted.")
