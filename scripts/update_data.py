"""Piyasa verilerini günceller: FX (TCMB), Altın & BIST (yfinance), TÜFE & KFE (TCMB EVDS - opsiyonel).

Her kaynak bağımsız try/except içinde çalışır; biri başarısız olursa diğerleri güncellenir
ve mevcut veriler korunur.

TÜFE (cpi.json) ve KFE (kfe.json):
  - Otomatik çekmek için TCMB EVDS API anahtarı gerekir. Ortam değişkeni EVDS_API_KEY
    tanımlıysa TÜFE için TP.FG.J0 (2003=100), KFE için TP.HKFE01 serisi çekilir.
  - Anahtar yoksa mevcut cpi.json / kfe.json korunur (uygulama, eksik dönemleri son 12 ayın
    trendiyle tahmin eder ve "tahmini" olarak işaretler).
"""
import json
import os
from datetime import datetime
import xml.etree.ElementTree as ET

import httpx

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE, "data")
EVDS_KEY = os.environ.get("EVDS_API_KEY")


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


# ---------------------------------------------------------------- FX (TCMB)
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
        for curr in root.findall("Currency"):
            code = curr.get("Kod")
            if code in ("USD", "EUR"):
                try:
                    rates[code] = float(curr.find("ForexBuying").text)
                except Exception:
                    pass
        return rates if rates.get("USD") else None
    except Exception:
        return None


def get_first_valid_tcmb_day(year, month):
    for day in range(1, 32):
        rates = fetch_tcmb_rate(year, month, day)
        if rates:
            return f"{year}-{month:02d}-{day:02d}", rates
    return None, None


def update_fx():
    records = []
    now = datetime.now()
    for year in range(2015, now.year + 1):
        for month in range(1, 13):
            if year == now.year and month > now.month:
                break
            d, rates = get_first_valid_tcmb_day(year, month)
            if d:
                records.append({"date": d, "usd_try": rates.get("USD"), "eur_try": rates.get("EUR")})
    if records:
        save_json("fx.json", records)
        print("FX records:", len(records))


# ---------------------------------------------------------------- Altın & BIST (yfinance)
def _flatten(df):
    df.columns = [" ".join(c).strip() if isinstance(c, tuple) else c for c in df.columns]
    return df


def fetch_yf(symbol, period="12y"):
    import yfinance as yf
    import pandas as pd
    try:
        df = _flatten(yf.download(symbol, period=period, interval="1mo", progress=False, auto_adjust=True))
        if df.empty:
            return None
        df = df.reset_index()
        df["date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None).dt.strftime("%Y-%m-%d")
        return df
    except Exception as e:
        print("YF error", symbol, e)
        return None


def update_gold():
    import pandas as pd
    existing = load_json("gold.json")
    gc, usd = fetch_yf("GC=F"), fetch_yf("USDTRY=X")
    if gc is None or usd is None:
        print("Gold fetch failed, keeping existing.")
        return
    df = pd.merge(gc[["date", "Close GC=F"]], usd[["date", "Close USDTRY=X"]], on="date")
    df["gram_try"] = df["Close GC=F"] * df["Close USDTRY=X"] / 31.1035
    rows = [{"date": r["date"], "price_try": float(r["gram_try"])} for _, r in df.iterrows()]
    merged = {r["date"]: r for r in existing}
    for r in rows:
        merged[r["date"]] = r
    save_json("gold.json", sorted(merged.values(), key=lambda x: x["date"]))
    print("Gold records:", len(merged))


def update_bist():
    existing = load_json("bist.json")
    # GYO: tekil şirket değil, BIST Gayrimenkul Yat. Ort. ENDEKSİ (XGMYO)
    bist, gyo = fetch_yf("XU100.IS"), fetch_yf("XGMYO.IS")
    merged = {r["date"]: r for r in existing}
    if bist is not None:
        for _, row in bist.iterrows():
            merged.setdefault(row["date"], {"date": row["date"]})["bist100"] = float(row["Close XU100.IS"])
    if gyo is not None:
        # Endeks başarıyla geldiyse eski gyox değerlerini (İş GYO) tamamen değiştir
        for v in merged.values():
            v.pop("gyox", None)
        for _, row in gyo.iterrows():
            merged.setdefault(row["date"], {"date": row["date"]})["gyox"] = float(row["Close XGMYO.IS"])
    else:
        print("XGMYO endeksi alınamadı; mevcut gyox korunuyor.")
    rows = [v for v in merged.values() if v.get("bist100")]
    save_json("bist.json", sorted(rows, key=lambda x: x["date"]))
    print("BIST records:", len(rows))


# ---------------------------------------------------------------- TÜFE & KFE (TCMB EVDS, opsiyonel)
def fetch_evds(series_code):
    """TCMB EVDS'den aylık seri çeker. EVDS_KEY yoksa None döner."""
    if not EVDS_KEY:
        return None
    url = (
        f"https://evds2.tcmb.gov.tr/service/evds/series={series_code}"
        f"&startDate=01-01-2015&endDate=31-12-{datetime.now().year}"
        f"&type=json&frequency=5&aggregationTypes=avg"
    )
    try:
        r = httpx.get(url, headers={"key": EVDS_KEY}, timeout=30)
        r.raise_for_status()
        items = r.json().get("items", [])
        out = []
        col = series_code.replace(".", "_")
        for it in items:
            raw = it.get(col) or it.get(col.replace("_", "-"))
            date = it.get("Tarih")  # 'YYYY-M' veya 'M-YYYY'
            if raw in (None, "", "null") or not date:
                continue
            try:
                a, b = date.replace("/", "-").split("-")
                y, m = (a, b) if len(a) == 4 else (b, a)
                out.append((f"{int(y):04d}-{int(m):02d}-01", float(raw)))
            except Exception:
                continue
        return out or None
    except Exception as e:
        print("EVDS error", series_code, e)
        return None


def update_cpi():
    data = fetch_evds("TP.FG.J0")  # TÜFE genel, 2003=100
    if not data:
        print("CPI: EVDS anahtarı yok veya çekilemedi, mevcut cpi.json korunuyor.")
        return
    merged = {r["date"]: r["cpi_index"] for r in load_json("cpi.json")}
    for d, v in data:
        merged[d] = v
    save_json("cpi.json", [{"date": d, "cpi_index": v} for d, v in sorted(merged.items())])
    print("CPI records:", len(merged))


def update_kfe():
    data = fetch_evds("TP.HKFE01")  # Konut Fiyat Endeksi (Türkiye geneli)
    if not data:
        print("KFE: EVDS anahtarı yok veya çekilemedi, mevcut kfe.json korunuyor.")
        return
    merged = {r["date"]: r for r in load_json("kfe.json")}
    for d, v in data:
        merged[d] = {"date": d, "region_code": "TR", "index": v}
    save_json("kfe.json", sorted(merged.values(), key=lambda x: x["date"]))
    print("KFE records:", len(merged))


if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)
    for fn in (update_fx, update_gold, update_bist, update_cpi, update_kfe):
        try:
            fn()
        except Exception as e:
            print(f"{fn.__name__} failed: {e}")
    print("Done.")
