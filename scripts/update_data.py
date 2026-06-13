import json
import os
from datetime import datetime
import httpx
import xml.etree.ElementTree as ET
import yfinance as yf
import pandas as pd

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


def fetch_tcmb_rate(year, month, day):
    date_str = f"{day:02d}{month:02d}{year}"
    folder = f"{year}{month:02d}"
    url = f"https://www.tcmb.gov.tr/kurlar/{folder}/{date_str}.xml"
    try:
        r = httpx.get(url, timeout=20)
        if r.status_code != 200:
            return None
        root = ET.fromstring(r.text)
        rates = {}
        for curr in root.findall('Currency'):
            code = curr.get('Kod')
            if code in ('USD', 'EUR'):
                try:
                    rates[code] = float(curr.find('ForexBuying').text)
                except Exception:
                    pass
        if rates.get('USD'):
            return rates
    except Exception:
        return None
    return None


def get_first_valid_tcmb_day(year, month):
    day = 1
    while day <= 31:
        rates = fetch_tcmb_rate(year, month, day)
        if rates:
            return f"{year}-{month:02d}-{day:02d}", rates
        day += 1
    return None, None


def update_fx():
    records = []
    now = datetime.now()
    end_year, end_month = now.year, now.month
    for year in range(2015, end_year + 1):
        for month in range(1, 13):
            if year == end_year and month > end_month:
                break
            d, rates = get_first_valid_tcmb_day(year, month)
            if d:
                records.append({
                    "date": d,
                    "usd_try": rates.get("USD"),
                    "eur_try": rates.get("EUR"),
                })
    save_json("fx.json", records)
    print("FX records:", len(records))


def flatten_yf(df):
    df.columns = [' '.join(col).strip() if isinstance(col, tuple) else col for col in df.columns]
    return df


def fetch_yf(symbol, period="10y"):
    try:
        df = flatten_yf(yf.download(symbol, period=period, interval="1mo", progress=False, auto_adjust=True))
        if df.empty:
            return None
        df = df.reset_index()
        df["date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None).dt.strftime("%Y-%m-%d")
        return df
    except Exception as e:
        print("YF error", symbol, e)
        return None


def update_gold():
    existing = load_json("gold.json")
    gc = fetch_yf("GC=F")
    usd = fetch_yf("USDTRY=X")
    if gc is None or usd is None:
        print("Gold fetch failed, keeping existing.")
        return
    df = pd.merge(gc[['date', 'Close GC=F']], usd[['date', 'Close USDTRY=X']], on='date')
    df['gram_try'] = df['Close GC=F'] * df['Close USDTRY=X'] / 31.1035
    rows = [{"date": row["date"], "price_try": float(row["gram_try"])} for _, row in df.iterrows()]
    merged = {r["date"]: r for r in existing}
    for r in rows:
        merged[r["date"]] = r
    save_json("gold.json", sorted(merged.values(), key=lambda x: x["date"]))
    print("Gold records:", len(merged))


def update_bist():
    existing = load_json("bist.json")
    bist = fetch_yf("XU100.IS")
    gyo = fetch_yf("ISGYO.IS")
    merged = {r["date"]: r for r in existing}
    if bist is not None:
        for _, row in bist.iterrows():
            d = row["date"]
            if d not in merged:
                merged[d] = {"date": d}
            merged[d]["bist100"] = float(row["Close XU100.IS"])
    if gyo is not None:
        for _, row in gyo.iterrows():
            d = row["date"]
            if d not in merged:
                merged[d] = {"date": d}
            merged[d]["gyox"] = float(row["Close ISGYO.IS"])
    rows = [v for v in merged.values() if v.get("bist100")]
    save_json("bist.json", sorted(rows, key=lambda x: x["date"]))
    print("BIST records:", len(rows))


if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)
    update_fx()
    update_gold()
    update_bist()
    print("Done.")
