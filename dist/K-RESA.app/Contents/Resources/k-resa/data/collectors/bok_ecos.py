"""한국은행 ECOS API 데이터 수집기"""

import requests
import pandas as pd
from datetime import datetime, timedelta
from utils.constants import BOK_STAT_CODES
from utils.helpers import load_cache, save_cache


class BokEcosCollector:
    """한국은행 경제통계시스템(ECOS) API 수집기

    API URL: /StatisticSearch/{api_key}/json/kr/{start_no}/{end_no}/{stat_code}/{period}/{start}/{end}/{item_code}
    """

    BASE_URL = "https://ecos.bok.or.kr/api"

    # 통계표별 올바른 item_code 매핑
    ITEM_CODES = {
        "cpi": "0",               # 901Y009 소비자물가 총지수
        "ppi": "*AA",             # 404Y014 생산자물가 총지수
        "import_price": "*AA",    # 401Y015 수입물가 총지수
        "base_rate": "0101000",   # 722Y001 한국은행 기준금리
        "exchange_rate_m": "0000001",  # 731Y004 원/미국달러(매매기준율)
        "export": "T002",         # 901Y118 수출금액
        "import": "T004",         # 901Y118 수입금액
        "current_account": "SA000",  # 301Y017 경상수지
        "gdp_real_sa": "1400",    # 200Y104 국내총생산(시장가격, GDP)
    }

    # 주기 매핑
    PERIODS = {
        "cpi": "M", "ppi": "M", "import_price": "M",
        "base_rate": "D",
        "exchange_rate_m": "M",
        "export": "M", "import": "M",
        "current_account": "M",
        "gdp_real_sa": "Q",
    }

    def __init__(self, api_key: str = ""):
        self.api_key = api_key

    def _request(self, stat_code: str, period: str,
                 start: str, end: str, item_code: str = "0",
                 start_no: int = 1, end_no: int = 100) -> list[dict]:
        """ECOS API 호출"""
        if not self.api_key:
            raise ValueError("한국은행 ECOS API 키가 설정되지 않았습니다.")

        url = (
            f"{self.BASE_URL}/StatisticSearch/{self.api_key}/json/kr/"
            f"{start_no}/{end_no}/{stat_code}/{period}/{start}/{end}/{item_code}"
        )

        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        if "StatisticSearch" in data and "row" in data["StatisticSearch"]:
            return data["StatisticSearch"]["row"]

        if "RESULT" in data:
            code = data["RESULT"].get("CODE", "")
            msg = data["RESULT"].get("MESSAGE", "")
            if code != "INFO-000":
                raise ValueError(f"ECOS API 오류 [{code}]: {msg}")

        return []

    def get_series(self, stat_name: str, months: int = 12) -> pd.DataFrame:
        """통계 시계열 데이터 반환"""
        stat_code = BOK_STAT_CODES.get(stat_name, stat_name)
        item_code = self.ITEM_CODES.get(stat_name, "0")
        period = self.PERIODS.get(stat_name, "M")
        cache_key = f"bok_{stat_code}_{item_code}_{months}m"

        cached = load_cache(cache_key)
        if cached is not None:
            return pd.DataFrame(cached)

        end = datetime.now()
        start = end - timedelta(days=months * 30)

        if period == "D":
            start_str = start.strftime("%Y%m%d")
            end_str = end.strftime("%Y%m%d")
        elif period == "Q":
            start_str = f"{start.year}Q1"
            end_str = f"{end.year}Q4"
        else:
            start_str = start.strftime("%Y%m")
            end_str = end.strftime("%Y%m")

        rows = self._request(stat_code, period, start_str, end_str, item_code)

        if not rows:
            return pd.DataFrame(columns=["date", "value"])

        df = pd.DataFrame(rows)
        df = df.rename(columns={"TIME": "date", "DATA_VALUE": "value"})
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df = df[["date", "value"]].dropna()

        save_cache(cache_key, df.to_dict(orient="list"))
        return df

    def get_latest(self, stat_name: str) -> float:
        """최신값 반환"""
        df = self.get_series(stat_name, months=6)
        if df.empty:
            raise ValueError(f"데이터 없음: {stat_name}")
        return float(df.iloc[-1]["value"])

    def get_key_indicators(self) -> dict:
        """주요 한국 경제 지표 일괄 조회"""
        indicators = {}

        # CPI 전년동월비 (지수 → %로 변환)
        try:
            df = self.get_series("cpi", months=15)
            if len(df) >= 13:
                latest = df.iloc[-1]["value"]
                year_ago = df.iloc[-13]["value"]
                indicators["cpi_yoy"] = round((latest / year_ago - 1) * 100, 1)
        except Exception:
            pass

        # PPI 전년동월비
        try:
            df = self.get_series("ppi", months=15)
            if len(df) >= 13:
                latest = df.iloc[-1]["value"]
                year_ago = df.iloc[-13]["value"]
                indicators["ppi_yoy"] = round((latest / year_ago - 1) * 100, 1)
        except Exception:
            pass

        # 기준금리 (일별 → 최신)
        try:
            indicators["base_rate"] = self.get_latest("base_rate")
        except Exception:
            pass

        # 환율 (월평균)
        try:
            indicators["usd_krw_bok"] = self.get_latest("exchange_rate_m")
        except Exception:
            pass

        # 무역수지 (수출 - 수입, 천달러 → 십억달러)
        try:
            export_val = self.get_latest("export")
            import_val = self.get_latest("import")
            indicators["trade_balance"] = round((export_val - import_val) / 1_000_000, 1)
        except Exception:
            pass

        # 경상수지 (백만달러 → 십억달러)
        try:
            ca = self.get_latest("current_account")
            indicators["current_account"] = round(ca / 1000, 1)
        except Exception:
            pass

        # GDP 성장률 (계절조정 실질, 전기비)
        try:
            df = self.get_series("gdp_real_sa", months=24)
            if len(df) >= 2:
                latest = df.iloc[-1]["value"]
                prev = df.iloc[-2]["value"]
                indicators["gdp_growth"] = round((latest / prev - 1) * 100, 1)
        except Exception:
            pass

        return indicators
