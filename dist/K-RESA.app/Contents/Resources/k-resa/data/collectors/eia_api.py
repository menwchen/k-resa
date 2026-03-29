"""EIA(미국 에너지정보청) API 데이터 수집기"""

import requests
import pandas as pd
from datetime import datetime, timedelta
from utils.helpers import load_cache, save_cache, get_api_key


class EiaCollector:
    """미국 에너지정보청(EIA) API 수집기"""

    BASE_URL = "https://api.eia.gov/v2"

    # 주요 시리즈
    SERIES = {
        "crude_production": "petroleum/crd/crpdn",
        "crude_imports": "petroleum/move/imp",
        "lng_exports": "natural-gas/move/expc",
        "henry_hub": "natural-gas/pri/fut",
    }

    def __init__(self, api_key: str = ""):
        self.api_key = api_key or get_api_key("eia")

    def _request(self, route: str, params: dict = None) -> list[dict]:
        """EIA API v2 호출"""
        if not self.api_key:
            raise ValueError("EIA API 키가 설정되지 않았습니다.")

        url = f"{self.BASE_URL}/{route}/data/"
        default_params = {
            "api_key": self.api_key,
            "frequency": "monthly",
            "sort[0][column]": "period",
            "sort[0][direction]": "desc",
            "length": 24,
        }
        if params:
            default_params.update(params)

        resp = requests.get(url, params=default_params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        return data.get("response", {}).get("data", [])

    def get_series(self, series_name: str, months: int = 12) -> pd.DataFrame:
        """EIA 시계열 데이터 반환"""
        route = self.SERIES.get(series_name, series_name)
        cache_key = f"eia_{series_name}_{months}m"

        cached = load_cache(cache_key)
        if cached is not None:
            return pd.DataFrame(cached)

        rows = self._request(route, {"length": months})
        if not rows:
            return pd.DataFrame(columns=["date", "value"])

        df = pd.DataFrame(rows)
        if "period" in df.columns and "value" in df.columns:
            df = df.rename(columns={"period": "date"})
            df["date"] = pd.to_datetime(df["date"])
            df["value"] = pd.to_numeric(df["value"], errors="coerce")
            df = df[["date", "value"]].dropna().sort_values("date")

        save_cache(cache_key, df.to_dict(orient="list"))
        return df

    def get_global_oil_supply(self) -> dict:
        """글로벌 원유 공급 현황 요약"""
        cache_key = "eia_global_oil_summary"
        cached = load_cache(cache_key)
        if cached:
            return cached

        try:
            prod = self._request("petroleum/crd/crpdn", {"length": 1})
            summary = {
                "source": "EIA",
                "data": prod[:5] if prod else [],
                "retrieved_at": datetime.now().isoformat(),
            }
            save_cache(cache_key, summary)
            return summary
        except Exception:
            return {"source": "EIA", "data": [], "error": "데이터 수집 실패"}
