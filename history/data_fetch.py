import os, sys, django, pandas as pd, yfinance as yf

# ── Django 환경 설정 ───────────────────────────────────────────────
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from core.models import DailyPrice

# ── Yahoo Finance 데이터 가져오기 ────────────────────────────────
def fetch_data(symbol: str, period="10y", interval="1d") -> pd.DataFrame:
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period, interval=interval)
    df.reset_index(inplace=True)
    df = df[['Date', 'Close', 'Open', 'High', 'Low', 'Volume']]
    df = df.rename(columns={
        "Date": "date",
        "Close": "close",
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Volume": "volume"
    })
    df['symbol'] = symbol
    return df

# ── 데이터베이스 저장 ────────────────────────────────────────────
def save_to_db(df: pd.DataFrame):
    records = [
        DailyPrice(
            symbol=row.symbol,
            date=row.date,
            open=row.open,
            high=row.high,
            low=row.low,
            close=row.close,
            volume=row.volume
        )
        for row in df.itertuples()
    ]
    DailyPrice.objects.bulk_create(records, ignore_conflicts=True)

# ── 메인 실행부 ─────────────────────────────────────────────────
if __name__ == "__main__":
    symbol = "QQQ"
    df = fetch_data(symbol)
    print("[원본 5행]")
    print(df.head())
    save_to_db(df)
    print("[데이터 저장 완료]")
