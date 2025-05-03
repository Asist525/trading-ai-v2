# -*- coding: utf-8 -*-
"""
Korea Investment Securities Open API – Authentication & Common HTTP Wrapper
(env-only + legacy-compat + 403-retry)  2025-05-01
"""
import os, json, copy, time, requests
from datetime import datetime, timedelta
from collections import namedtuple

# ───────────────────────────── 0. 기본 헤더
MY_AGENT = os.getenv("MY_AGENT", "kis-client/1.0")
_BASE_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "text/plain",
    "charset": "UTF-8",
    "User-Agent": MY_AGENT,
}

# ───────────────────────────── 1. 환경변수 → CFG
def _env(key, default=None):
    v = os.getenv(key, default)
    if v is None:
        raise EnvironmentError(f"[KIS_AUTH] 환경변수 {key} 가 설정되지 않았습니다.")
    return v

def _load_cfg():
    mode = _env("KIS_MODE", "real").lower()
    is_paper = mode in ("paper", "vps")
    return {
        "mode": mode,
        "is_paper": is_paper,
        "prod": _env("KIS_PROD_CODE", "01"),
        "app_key": _env("APP_KEY_PAPER")   if is_paper else _env("APP_KEY_REAL"),
        "app_sec": _env("APP_SECRET_PAPER")if is_paper else _env("APP_SECRET_REAL"),
        "base_url": _env("KIS_API_VPS")    if is_paper else _env("KIS_API_REAL"),
        "acct": _env("KIS_ACCT_PAPER")     if is_paper else _env("KIS_ACCT_REAL"),
    }

_CFG = _load_cfg()

# ───────────────────────────── 2. 토큰 캐싱
TOKEN_DIR = os.getenv("KIS_TOKEN_DIR", "/tmp/kis")
os.makedirs(TOKEN_DIR, exist_ok=True)
TOKEN_PATH = os.path.join(TOKEN_DIR, f"KIS{datetime.today():%Y%m%d}")

def _save_token(tok, exp):
    with open(TOKEN_PATH, "w", encoding="utf-8") as f:
        json.dump({"token": tok, "expired": exp}, f)

def _read_token():
    try:
        with open(TOKEN_PATH, encoding="utf-8") as f:
            d = json.load(f)
        if datetime.strptime(d["expired"], "%Y-%m-%d %H:%M:%S") > datetime.now():
            return d["token"]
    except Exception:
        pass
    return None

# ───────────────────────────── 3. 전역 상태
TREnv = namedtuple(
    "TRENV",
    ["token", "app_key", "app_sec", "url", "my_acct", "my_prod", "is_paper"],
)
_TRENV: TREnv | None = None
_LAST_AUTH = datetime.min

def getTREnv():          # kis_domstk.py 가 기대
    return _TRENV

# ───────────────────────────── 4. 인증 (403 재시도 내장)
def _build_trenv(token: str) -> TREnv:
    return TREnv(
        token=f"Bearer {token}",
        app_key=_CFG["app_key"],
        app_sec=_CFG["app_sec"],
        url=_CFG["base_url"],
        my_acct=_CFG["acct"],
        my_prod=_CFG["prod"],
        is_paper=_CFG["is_paper"],
    )

def auth(force=False):
    global _TRENV, _LAST_AUTH

    # 캐시 사용
    if not force:
        cached = _read_token()
        if cached:
            _TRENV = _build_trenv(cached)
            _apply_headers()
            return

    payload = {
        "grant_type": "client_credentials",
        "appkey": _CFG["app_key"],
        "appsecret": _CFG["app_sec"],
    }
    url = f"{_CFG['base_url']}/oauth2/tokenP"
    max_retry = int(os.getenv("KIS_AUTH_RETRY_MAX", 5))
    wait_sec  = int(os.getenv("KIS_AUTH_RETRY_WAIT", 60))

    for i in range(max_retry):
        r = requests.post(url, headers=_BASE_HEADERS, data=json.dumps(payload))
        if r.status_code == 200:
            break
        if r.status_code == 403 and r.headers.get("Content-Type","").startswith("application/json") \
           and r.json().get("error_code") == "EGW00133" and i < max_retry-1:
            print(f"[AUTH RETRY] 403/EGW00133 – {wait_sec}s 후 재시도 ({i+1}/{max_retry})")
            time.sleep(wait_sec)
            continue
        raise RuntimeError(f"[AUTH FAIL] {r.status_code}\n{r.text}")

    if r.status_code != 200:
        raise RuntimeError(f"[AUTH FAIL] {r.status_code}\n{r.text}")

    tok, exp = r.json()["access_token"], r.json()["access_token_token_expired"]
    _save_token(tok, exp)
    _TRENV = _build_trenv(tok)
    _apply_headers()
    _LAST_AUTH = datetime.now()

def _apply_headers():
    _BASE_HEADERS.update({
        "authorization": _TRENV.token,
        "appkey": _TRENV.app_key,
        "appsecret": _TRENV.app_sec,
    })

def _auto_reauth():
    if datetime.now() - _LAST_AUTH > timedelta(hours=24):
        auth(force=True)

# ───────────────────────────── 5. 응답 래퍼 + compat
class APIResp:
    def __init__(self, resp: requests.Response):
        self._resp = resp
        self._status = resp.status_code
        self._json = resp.json() if resp.headers.get("Content-Type","").startswith("application/json") else {}
        self._body = namedtuple("body", self._json.keys())(**self._json) if self._json else None
    def ok(self):  return self._status==200 and getattr(self._body,"rt_cd","")=="0"
    def err(self): return "" if self.ok() else f"[{getattr(self._body,'msg_cd','')}] {getattr(self._body,'msg1','')}"
    def json(self):return self._json

def _build_hdr_namedtuple(resp):
    sanitized = {k.lower().replace("-", "_"): v for k, v in resp.headers.items()}
    return namedtuple("header", sanitized.keys())(*sanitized.values())


class APIRespCompat(APIResp):
    def getBody(self):         return self._body
    def getHeader(self):       return _build_hdr_namedtuple(self._resp)
    def isOK(self):            return self.ok()
    def getErrorCode(self):    return getattr(self._body,"msg_cd","")
    def getErrorMessage(self): return getattr(self._body,"msg1","")

# ───────────────────────────── 6. HTTP wrapper
def _get_base_header():
    _auto_reauth()
    return copy.deepcopy(_BASE_HEADERS)

def _url_fetch(api_path, tr_id, tr_cont,
               params=None, post=False, postFlag=False, extra_headers=None) -> APIRespCompat:

    if postFlag: post = True
    url = f"{_TRENV.url}{api_path}"
    hdr = _get_base_header()

    if tr_id and tr_id[0] in ("T","J","C") and _TRENV.is_paper:
        tr_id = "V"+tr_id[1:]
    hdr.update({"tr_id":tr_id,"tr_cont":tr_cont,"custtype":"P", **(extra_headers or {})})

    resp = requests.post(url, headers=hdr, data=json.dumps(params or {})) if post \
           else requests.get(url, headers=hdr, params=params or {})
    return APIRespCompat(resp)

# ───────────────────────────── 7. export list
__all__ = ["auth", "_url_fetch", "APIResp", "_TRENV", "_get_base_header", "getTREnv"]
