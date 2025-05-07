"""
normalization.py
----------------------
확장-윈도우 1단계:
1) DB에 이미 저장된 원본 DailyPrice 중, 해당 종목의 ‘첫 날짜’ 확인
2) 그 날짜의 다음 달 1일을 시작점(start_date)으로 1년치 구간(end_date)을 계산
3) 해당 구간 데이터를 DB에서 로드 → 정규화(Z-score)만 수행
4) 정규화된 DataFrame을 화면에 출력
"""

import os, sys, django, pandas as pd
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from sklearn.preprocessing import StandardScaler
import numpy as np
import argparse
from sklearn.preprocessing import StandardScaler


# ── Django 환경 설정 ───────────────────────────────────────────────
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from core.models import DailyPrice

print("---------------------------------------------------restart")

# ── 유틸: 다음 달 1일 계산 ────────────────────────────────────────
def next_month_first(ts: pd.Timestamp) -> pd.Timestamp:
    return (ts + relativedelta(months=1)).replace(day=1)

# ── 1년 구간 원본 데이터 로드 ────────────────────────────────────
def load_window(symbol: str, years: int = 2, lookback: int = 252, horizon: int = 40) -> pd.DataFrame:
    # 1) 가장 오래된 날짜
    first_row = (
        DailyPrice.objects.filter(symbol=symbol)
        .order_by("date")
        .values("date")
        .first()
    )
    if not first_row:
        raise ValueError(f"{symbol} 데이터가 DB에 없습니다.")

    # 2) 시작일 (최초 데이터의 다음 달 1일)
    first_date = pd.to_datetime(first_row["date"])
    start_date = next_month_first(first_date)

    # 3) 종료일 (lookback + horizon = 274 영업일)
    end_date = start_date + relativedelta(years=years) - timedelta(days=1) 
    end_date += pd.tseries.offsets.BDay(horizon + 10)
    print(f"날짜 : {start_date} ~ {end_date}")
    # 4) 데이터 로드
    qs = (
        DailyPrice.objects.filter(symbol=symbol, date__range=(start_date, end_date))
        .values("date", "open", "high", "low", "close", "volume")
        .order_by("date")
    )
    df = pd.DataFrame.from_records(qs)
    
    if df.empty:
        raise ValueError(f"{symbol}의 선택한 1년+{horizon}일 구간에 데이터가 없습니다.")

    # 5) 날짜 인덱스 설정 
    df.set_index("date", inplace=True)

    # 6) 결측치 제거
    df.dropna(inplace=True)

    return df



# ── 정규화(Z-score) ────────────────────────────────────────────────
def normalize(df: pd.DataFrame, scaler: StandardScaler | None = None):
    """df → (정규화된 DataFrame, fitted StandardScaler)

    새 데이터를 변환할 때는 scaler 인자로 기존 스케일러를 넘기면 됨.
    """
    feats = df[["open", "high", "low", "close", "volume"]].copy()
    feats["volume"] = np.log1p(feats["volume"])      # 로그 변환

    if scaler is None:
        scaler = StandardScaler()
        scaled = scaler.fit_transform(feats)
    else:                               # 예측 단계
        scaled = scaler.transform(feats)

    norm_df = pd.DataFrame(
        scaled, columns=["open", "high", "low", "close", "volume"], index=df.index
    ).reset_index()                     # date 열 복원

    return norm_df, scaler

# ── 메인 실행부 ───────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="확장-윈도우 정규화 스크립트")
    parser.add_argument("--symbol", type=str, default="QQQ", help="정규화할 종목 심볼")
    args = parser.parse_args()

    # 원본 데이터 로드
    raw_df = load_window(args.symbol)
    print("[원본 5행]")
    pd.set_option('display.max_rows', None)
    print(raw_df)

    # 데이터 정규화
    norm_df = normalize(raw_df)
    print("\n[정규화 결과 5행]")
    pd.set_option('display.max_rows', None)
    print(norm_df)
    pd.reset_option('display.max_rows')
