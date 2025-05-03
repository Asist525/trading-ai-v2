# -*- coding: utf-8 -*-
"""
kis_module.py ― Korea Investment OpenAPI 공통 유틸‧샘플 호출 집합
(작성 2025-05-01)

● 주요 함수
────────────────────────────────────────────────────────────────────
init_auth()                 ─ 씬 전체 인증 초기화 (토큰 발급 + env 반환)
is_tradable()               ─ 지금이 주식 주문 가능 시점인지 판단
order_cash_buy()            ─ 현금 매수주문 (예: buy 071050 10주 65,000)
order_cash_sell()           ─ 현금 매도주문
order_modify_or_cancel()    ─ 정정‧취소 주문
query_*()                   ─ 각종 조회 래퍼 (잔고, 체결, 현재가 …)

● 사용 예시
────────────────────────────────────────────────────────────────────
import kis_module as km

env = km.init_auth()                  # 1) 인증
if km.is_tradable():                  # 2) 주문 가능 시간인지 확인
    km.order_cash_buy("071050", 10, 65000)

bal = km.query_balance_list()         # 3) 잔고‧조회 함수 호출
print(bal)

"""

from __future__ import annotations

# ────────────────────────────────────────────────────────────────────
# 표준/외부 라이브러리
# ────────────────────────────────────────────────────────────────────
import datetime as dt
import sys
from typing import List, Tuple

import pandas as pd
import pytz

# ────────────────────────────────────────────────────────────────────
# KIS SDK 래퍼
# ────────────────────────────────────────────────────────────────────
import kis_auth as ka
import kis_domstk as kb

# ────────────────────────────────────────────────────────────────────
# 상수/전역
# ────────────────────────────────────────────────────────────────────
KST = pytz.timezone("Asia/Seoul")

#: 한국장 기본 거래 가능 시간대(원하는 대로 조정)
TRADING_WINDOWS: List[Tuple[dt.time, dt.time]] = [
    (dt.time(9, 0), dt.time(15, 30)),   # 정규장 (장전포함)
    (dt.time(15, 40), dt.time(18, 0)),  # 시간외단일가(예시)
]

__all__ = [
    # 초기화/유틸
    "init_auth",
    "is_tradable",
    # 주문
    "order_cash_buy",
    "order_cash_sell",
    "order_modify_or_cancel",
    # 조회
    "query_psbl_rvsecncl_list",
    "query_daily_ccld_obj",
    "query_daily_ccld_list",
    "query_balance_obj",
    "query_balance_list",
    "query_psbl_order",
    "query_reservation_list",
    "query_balance_pl_obj",
    "query_balance_pl_list",
    "query_credit_psamount",
    "query_period_trade_profit_obj",
    "query_period_trade_profit_list",
    "query_period_profit_obj",
    "query_period_profit_list",
    "query_price",
    "query_ccnl",
    "query_daily_price",
    "query_asking_or_expect",
    "query_investor",
    "query_member",
    "query_itemchartprice_now",
    "query_itemchartprice_period",
    "query_time_itemconclusion",
    "query_daily_overtime_price",
    "query_intraday_chart",
    "query_price_v2",
    "query_etf_price",
    "query_nav_comparison",
    "query_holiday",
]

# ────────────────────────────────────────────────────────────────────
# 1. 인증 초기화
# ────────────────────────────────────────────────────────────────────
def init_auth(force: bool = False):
    """토큰 발급 + 환경 정보 반환"""
    ka.auth(force=force)
    env = ka.getTREnv()
    print(
        f"[AUTH] acct={env.my_acct}  prod={env.my_prod}  "
        f"mode={'PAPER' if env.is_paper else 'REAL'}"
    )
    return env


# ────────────────────────────────────────────────────────────────────
# 2. 장 운영일·시간 체크
# ────────────────────────────────────────────────────────────────────
def is_tradable(now: dt.datetime) -> bool:
    """휴일/주말/시간외 여부 판정"""
    # ① 주말
    if now.weekday() >= 5:
        return False

    # ② 휴장일 여부 (opnd_yn == 'N' 이면 휴장)
    holiday = kb.get_quotations_ch_holiday(dt=now.strftime("%Y%m%d"))
    if hasattr(holiday, 'opnd_yn'):
        if isinstance(holiday.opnd_yn, (pd.Series, pd.DataFrame)):
            if not holiday.empty and (holiday.opnd_yn.iloc[0] == "N"):
                return False
        elif holiday.opnd_yn == "N":
            return False

    # ③ 시간대
    for start, end in TRADING_WINDOWS:
        if start <= now.time() <= end:
            return True

    return False


# ────────────────────────────────────────────────────────────────────
# 3. 주문 래퍼
# ────────────────────────────────────────────────────────────────────
def _check_result(rt, msg: str = "API 호출 실패"):
    if rt is None:
        raise RuntimeError(msg)
    return rt


def order_cash_buy(itm_no: str, qty: int, price: int):
    """현금 매수주문"""
    rt = kb.get_order_cash(ord_dv="buy", itm_no=itm_no, qty=qty, unpr=price)
    return _check_result(rt, "현금매수 주문 실패")


def order_cash_sell(itm_no: str, qty: int, price: int):
    """현금 매도주문"""
    rt = kb.get_order_cash(ord_dv="sell", itm_no=itm_no, qty=qty, unpr=price)
    return _check_result(rt, "현금매도 주문 실패")


def order_modify_or_cancel(
    ord_orgno: str,
    orgn_odno: str,
    ord_dvsn: str,
    rvse_cncl_dvsn_cd: str,
    ord_qty: int,
    ord_unpr: int,
    qty_all_ord_yn: str = "Y",
):
    """정정/취소 주문"""
    rt = kb.get_order_rvsecncl(
        ord_orgno=ord_orgno,
        orgn_odno=orgn_odno,
        ord_dvsn=ord_dvsn,
        rvse_cncl_dvsn_cd=rvse_cncl_dvsn_cd,
        ord_qty=ord_qty,
        ord_unpr=ord_unpr,
        qty_all_ord_yn=qty_all_ord_yn,
    )
    return _check_result(rt, "정정/취소 주문 실패")


# ────────────────────────────────────────────────────────────────────
# 4. 조회 래퍼 (필요한 만큼 노출)
# ────────────────────────────────────────────────────────────────────
def query_psbl_rvsecncl_list():
    return kb.get_inquire_psbl_rvsecncl_lst()


def query_daily_ccld_obj(dv="01"):
    return kb.get_inquire_daily_ccld_obj(dv=dv)


def query_daily_ccld_list(dv="01"):
    return kb.get_inquire_daily_ccld_lst(dv=dv)


def query_balance_obj():
    return kb.get_inquire_balance_obj()


def query_balance_list():
    return kb.get_inquire_balance_lst()


def query_psbl_order(pdno="", ord_unpr=0):
    return kb.get_inquire_psbl_order(pdno=pdno, ord_unpr=ord_unpr)


def query_reservation_list(inqr_strt_dt, inqr_end_dt):
    return kb.get_order_resv_ccnl(inqr_strt_dt=inqr_strt_dt, inqr_end_dt=inqr_end_dt)


def query_balance_pl_obj():
    return kb.get_inquire_balance_rlz_pl_obj()


def query_balance_pl_list():
    return kb.get_inquire_balance_rlz_pl_lst()


def query_credit_psamount():
    return kb.get_inquire_credit_psamount()


def query_period_trade_profit_obj():
    return kb.get_inquire_period_trade_profit_obj()


def query_period_trade_profit_list():
    return kb.get_inquire_period_trade_profit_lst()


def query_period_profit_obj():
    return kb.get_inquire_period_profit_obj()


def query_period_profit_list():
    return kb.get_inquire_period_profit_lst()


def query_price(itm_no: str):
    return kb.get_inquire_price(itm_no=itm_no)


def query_ccnl(itm_no: str):
    return kb.get_inquire_ccnl(itm_no=itm_no)


def query_daily_price(itm_no: str, period_code="D"):
    return kb.get_inquire_daily_price(itm_no=itm_no, period_code=period_code)


def query_asking_or_expect(itm_no: str, expect=False):
    return kb.get_inquire_asking_price_exp_ccn(
        output_dv="2" if expect else "1", itm_no=itm_no
    )


def query_investor(itm_no: str):
    return kb.get_inquire_investor(itm_no=itm_no)


def query_member(itm_no: str):
    return kb.get_inquire_member(itm_no=itm_no)


def query_itemchartprice_now(itm_no: str):
    return kb.get_inquire_daily_itemchartprice(itm_no=itm_no)


def query_itemchartprice_period(
    itm_no: str,
    output_dv="1",
    inqr_strt_dt=None,
    inqr_end_dt=None,
    period_code="D",
):
    return kb.get_inquire_daily_itemchartprice(
        output_dv=output_dv,
        itm_no=itm_no,
        inqr_strt_dt=inqr_strt_dt,
        inqr_end_dt=inqr_end_dt,
        period_code=period_code,
    )


def query_time_itemconclusion(itm_no: str, output_dv="1", inqr_hour=None):
    return kb.get_inquire_time_itemconclusion(
        output_dv=output_dv, itm_no=itm_no, inqr_hour=inqr_hour
    )


def query_daily_overtime_price(itm_no: str, output_dv="1"):
    return kb.get_inquire_daily_overtimeprice(output_dv=output_dv, itm_no=itm_no)


def query_intraday_chart(itm_no: str, output_dv="1", inqr_hour=None):
    return kb.get_inquire_time_itemchartprice(
        output_dv=output_dv, itm_no=itm_no, inqr_hour=inqr_hour
    )


def query_price_v2(itm_no: str):
    return kb.get_inquire_daily_price_2(itm_no=itm_no)


def query_etf_price(itm_no: str):
    return kb.get_quotations_inquire_price(itm_no=itm_no)


def query_nav_comparison(itm_no: str, output_dv="1"):
    return kb.get_quotations_nav_comparison_trend(
        output_dv=output_dv, itm_no=itm_no
    )


def query_holiday(dt_: str):
    return kb.get_quotations_ch_holiday(dt=dt_)


# ────────────────────────────────────────────────────────────────────
# 5. 모듈 직 실행 시 데모
# ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    env = init_auth()

    now = dt.datetime.now(KST)
    print(f"\n[DEMO] 현재 시각: {now}")

    if is_tradable(now):
        print("[DEMO] 장 운영 중 → 매수주문 시도")
        try:
            od = order_cash_buy("071050", 1, 65000)
            print("[DEMO] 주문 완료:", od)
        except RuntimeError as e:
            print("[DEMO] 주문 실패:", e, file=sys.stderr)
    else:
        print("[DEMO] 장 운영시간이 아님 → 주문 패스")

    print("\n[DEMO] 잔고 리스트")
    print(query_balance_list())
