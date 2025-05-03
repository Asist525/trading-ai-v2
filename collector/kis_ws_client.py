# collector/kis_ws_client.py
import os
import json
import time
import threading
from urllib.parse import quote

import asyncio

import requests
import websocket
import ssl

# ────────────── 환경 변수 ──────────────

STOCK_CODE = "005930" # 향후 종목 서치 기능으로 전환할 예정
KIS_MODE = "real" # virture이면 가상 설정 가능
KIS_PROD_CODE="01"

if KIS_MODE == "real":
    APP_KEY = "PS37wzsl8l576b6HpO0g5GulicDXoUvPPMbt"
    APP_SECRET = "alUamTBWWhB72dQ8j5i4CrWdB0Vf28SCokiq0OsveOGRrooFb9FT5eHoaMWNiSSVy3Yfnr+gnwkGdVmkSgt7YBjlx/dw/RJa2coNjYPItEVuVCDvo9xJyuJG4OrCoIvPdBoGW7ciiZ/FSKC7pqBZk/soZY1tGVsbWbxSfW7/NtnzJVZiQ2o="
    url = "https://openapi.koreainvestment.com:9443"
    ACCT = "46206968"
    print("현재모드: Real_mode")

else:
    APP_KEY    = "PSAoh7tBw2hF95F4jMuGfMtWhoiKzs88U3q4"
    APP_SECRET = "/DwOUbjwXQPKf1VEpcDETOZAN9aBF/NBpqFfdh1PhS59X1DVuXlaC8iHkr0dPVw6Bnkme5SzG8XlTtjVrCTxbEx6FTfnQ3VwXjh7OsmDWLb8JCQOE/ksC1uzTqUIQKzHb8yy5srRKHlAR/ph7WOnWeiL0CqxIb5t74P/VD143sT+WEBjkUE="
    url        = "https://openapivts.koreainvestment.com:29443"
    ACCT       = "12345678"
    print("현재모드: Virture_mode")

print(f"APPKEY = {APP_KEY}")
print(f"APPSECRET = {APP_SECRET}")

def get_approval(key, secret):
    headers = {"content-type": "application/json"}
    body = {"grant_type": "client_credentials",
            "appkey": key,
            "secretkey": secret}
    URL = f"{url}/oauth2/Approval"
    res = requests.post(URL, headers=headers, data=json.dumps(body))
    return res.json()["approval_key"]

# 실시간 체결 데이터에서 현재가 출력
def show_current_price(data):
    values = data.split("^")
    if len(values) > 2:
        print(f"현재가: {values[2]} 원")
    else:
        print("현재가 데이터 누락")

# 웹소켓 콜백
def on_open(ws):
    print("WebSocket 연결 성공")
    sub_msg = {
        "header": {
            "approval_key": APPROVAL_KEY,
            "custtype": "P",
            "tr_type": "1",
            "content-type": "utf8",
        },
        "body": {
            "input": {
                "tr_id": "H0STCNT0",
                "tr_key": STOCK_CODE,
            }
        }
    }
    ws.send(json.dumps(sub_msg))
    print("구독 요청 전송:", sub_msg)

def on_message(ws, message):
    if message.startswith("0|"):  # 실시간 데이터
        parts = message.split("|")
        if len(parts) >= 4 and parts[1] == "H0STCNT0":
            data_cnt = int(parts[2])
            show_current_price(parts[3])
    else:
        print("기타 수신 데이터:", message)

def on_error(ws, error):
    print("WebSocket 에러:", error)

def on_close(ws, code, msg):
    print(f"🔌 WebSocket 종료 code={code}, msg={msg}")

# WebSocket 실행 함수
def run_ws():
    host = "wss://ops.koreainvestment.com:21000"
    auth = f"{APP_KEY}|{APP_SECRET}|{APPROVAL_KEY}"
    query = (
        f"?authorization={quote(auth)}"
        f"&tr_type=1&tr_id=H0STCNT0&custtype=P"
        f"&tr_key={STOCK_CODE}&content-type=utf8"
    )
    ws = websocket.WebSocketApp(
        host + query,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    threading.Thread(target=lambda: ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE}), daemon=True).start()
    return ws

# ────────────── 진입점 ──────────────
if __name__ == "__main__":
    print("approval_key 요청 중...")
    APPROVAL_KEY = get_approval(APP_KEY, APP_SECRET)
    print("approval_key:", APPROVAL_KEY)

    ws_client = run_ws()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("종료 요청됨")
        ws_client.close()