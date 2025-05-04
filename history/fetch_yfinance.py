import os, sys, django, pandas as pd, yfinance as yf

# Django 환경 설정
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from core.models import DailyPrice

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

if __name__ == "__main__":
    symbol = "QQQ"
    df = fetch_data(symbol)
    print(df.head())
    save_to_db(df)
