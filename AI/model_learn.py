# ---------------------------------------------------------------------------
# model_learn.py (최종 수정본)
# ---------------------------------------------------------------------------
import argparse
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
from joblib import dump
from datetime import datetime
import sys, os

# ---------------------------------------------------------------------------
# project import (expanding_normalize.py must be at project root)
# ---------------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from normalization import load_window, normalize  # helper functions

# ---------------------------------------------------------------------------
# dataset builder
# ---------------------------------------------------------------------------

def build_dataset(df: pd.DataFrame, lookback: int, horizon: int):
    """Return X, y where:
        • X = flattened features of last `lookback` days (5 × lookback)
        • y = percentage change over next `horizon` days
    """
    feats = ["open", "high", "low", "close", "volume"]
    X_lst, y_lst, date_lst = [], [], []

    # 전체 데이터에서 (lookback + horizon) 길이를 고려
    for i in range(lookback, len(df) - horizon):
        # 1) 입력 데이터 (lookback 길이)
        window = df.iloc[i - lookback : i][feats].values.flatten()
        
        # 2) 타겟 데이터 (horizon 길이)
        pct_change = (
            df.iloc[i + horizon]["close"] - df.iloc[i]["close"]
        ) / df.iloc[i]["close"]
        
        # 3) 리스트에 추가
        X_lst.append(window)
        y_lst.append(pct_change)
        date_lst.append(df.index[i])  # 날짜 인덱스 유지

    return np.array(X_lst), np.array(y_lst), date_lst


# ---------------------------------------------------------------------------
# main function
# ---------------------------------------------------------------------------

def main(symbol: str, lookback: int, horizon: int):
    # 1. 데이터 로딩 및 정규화
    raw_df = load_window(symbol)
    if len(raw_df) < lookback + horizon:
        print("❗ DB 안에 영업일이 부족합니다. fetch_yfinance 로 더 끌어오거나 lookback을 줄여 주세요.")
        return
    
    # 정규화 (scaler 포함)
    norm_df, scaler = normalize(raw_df)
    norm_df.set_index("date", inplace=True)
    
    # 2. 데이터셋 생성
    X, y, dates = build_dataset(norm_df, lookback, horizon)
    split = int(len(X) * 0.8)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]
    dates_test      = dates[split:]

    # 3. 모델 학습
    model = Ridge(alpha=1.0)
    model.fit(X_train, y_train)

    # 4. 모델 성능 평가
    preds = model.predict(X_test)
    mae  = mean_absolute_error(y_test, preds)
    rmse = (mean_squared_error(y_test, preds, multioutput='raw_values').mean()) ** 0.5
    print(f"=== {symbol} | lookback={lookback} | horizon={horizon}d | samples={len(X)} ===")
    print(f"MAE  : {mae:.5f}\nRMSE : {rmse:.5f}\n")

    # 5. 모델 저장
    models_dir = Path(__file__).parent / "saved_models"
    models_dir.mkdir(exist_ok=True)

    stamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname   = f"{symbol}_ridge_lb{lookback}_h{horizon}_{stamp}.pkl"
    outpath = models_dir / fname

    dump(
        {
            "model"   : model,
            "scaler"  : scaler,
            "lookback": lookback,
            "horizon" : horizon,
            "feats"   : ["open", "high", "low", "close", "volume"],
        },
        outpath,
    )
    print(f"\nsaved: {outpath}\n")


# ---------------------------------------------------------------------------
# script entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", default="QQQ")
    p.add_argument("--lookback", type=int, default=252, help="days of history (≈1y)")
    p.add_argument("--horizon", type=int, default=22, help="days ahead (≈1mo)")
    args = p.parse_args()

    main(args.symbol, args.lookback, args.horizon)
