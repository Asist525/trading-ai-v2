# AI/predict.py

import argparse
from pathlib import Path
import pandas as pd
import numpy as np
from joblib import load
from normalization import load_window, normalize

# ---------------------------------------------------------------------------
# 모델 로드 함수
# ---------------------------------------------------------------------------
def load_model(symbol):
    models_dir = Path(__file__).parent / "saved_models"
    model_files = sorted(models_dir.glob(f"{symbol}_ridge_lb*.pkl"), reverse=True)

    if not model_files:
        raise FileNotFoundError(f"No saved model found for {symbol}")

    model_path = model_files[0]  # 가장 최신 모델 선택
    print(f"[INFO] Loaded model: {model_path}")
    model_data = load(model_path)

    return model_data


# ---------------------------------------------------------------------------
# 데이터셋 생성 (lookback 길이의 입력)
# ---------------------------------------------------------------------------
def prepare_features(norm_df, lookback):
    feats = ["open", "high", "low", "close", "volume"]

    # 최근 lookback 기간의 데이터만 추출
    recent_data = norm_df[feats].tail(lookback).values.flatten()
    print(f"[INFO] Input features: {recent_data.shape}")

    return recent_data.reshape(1, -1)


# ---------------------------------------------------------------------------
# 메인 예측 함수
# ---------------------------------------------------------------------------
def main(symbol: str, lookback: int):
    # 1. 모델 로드
    model_data = load_model(symbol)
    model = model_data["model"]
    scaler = model_data["scaler"]
    feats = model_data["feats"]

    # 2. 데이터 로드 및 정규화
    raw_df = load_window(symbol)
    if len(raw_df) < lookback:
        print("❗ DB 안에 충분한 데이터가 없습니다. fetch_yfinance 로 데이터를 확보하세요.")
        return
    
    norm_df, _ = normalize(raw_df)
    norm_df.set_index("date", inplace=True)

    # 3. 입력 데이터 준비
    X_input = prepare_features(norm_df, lookback)

    # 4. 예측
    pred = model.predict(X_input)[0]
    print(f"=== {symbol} | lookback={lookback} | predicted_pct_change = {pred:.5f} ===")


# ---------------------------------------------------------------------------
# 스크립트 엔트리 포인트
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", default="QQQ", help="Stock symbol (e.g., QQQ, AAPL)")
    p.add_argument("--lookback", type=int, default=252, help="Days of history (≈1y)")
    args = p.parse_args()

    main(args.symbol, args.lookback)
