import yfinance as yf
import pandas as pd

def fetch_one_year_data(symbol: str) -> pd.DataFrame:
    """
    지정된 종목(symbol)의 1년치 일봉 데이터를 가져옵니다.
    """
    ticker = yf.Ticker(symbol)
    df = ticker.history(period="1y", interval="1d")  # 1년, 일봉 기준
    df.reset_index(inplace=True)
    df = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]  # 필요한 컬럼만
    return df

if __name__ == "__main__":
    symbol = "AAPL"  # 예시 종목
    df = fetch_one_year_data(symbol)
    print(df.head())
    df.to_csv(f"data/{symbol}_1y.csv", index=False)
