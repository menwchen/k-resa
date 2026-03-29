"""FRED API 데이터 수집기"""

import pandas as pd
from datetime import datetime, timedelta
from utils.constants import FRED_SERIES
from utils.helpers import load_cache, save_cache


class FredCollector:
    """FRED(Federal Reserve Economic Data) API 수집기"""

    BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self._fred = None

    @property
    def fred(self):
        if self._fred is None:
            if not self.api_key:
                raise ValueError("FRED API 키가 설정되지 않았습니다. config/settings.yaml 또는 환경변수 KRESA_FRED_API_KEY를 설정하세요.")
            from fredapi import Fred
            self._fred = Fred(api_key=self.api_key)
        return self._fred

    def get_series(self, indicator: str, months: int = 6) -> pd.DataFrame:
        """지표의 시계열 데이터 반환"""
        series_id = FRED_SERIES.get(indicator, indicator)
        cache_key = f"fred_{series_id}_{months}m"

        cached = load_cache(cache_key)
        if cached is not None:
            return pd.DataFrame(cached)

        end = datetime.now()
        start = end - timedelta(days=months * 30)

        data = self.fred.get_series(
            series_id,
            observation_start=start.strftime("%Y-%m-%d"),
            observation_end=end.strftime("%Y-%m-%d"),
        )

        df = pd.DataFrame({"date": data.index, "value": data.values})
        df["date"] = pd.to_datetime(df["date"])
        df = df.dropna()

        save_cache(cache_key, df.to_dict(orient="list"))
        return df

    def get_latest(self, indicator: str) -> float:
        """지표의 최신값 반환"""
        series_id = FRED_SERIES.get(indicator, indicator)
        cache_key = f"fred_latest_{series_id}"

        cached = load_cache(cache_key, ttl_hours=6)
        if cached is not None:
            return float(cached)

        data = self.fred.get_series(series_id)
        latest = data.dropna().iloc[-1]

        save_cache(cache_key, float(latest))
        return float(latest)

    def get_multiple_latest(self, indicators: list[str]) -> dict[str, float]:
        """여러 지표의 최신값을 한번에 반환"""
        results = {}
        for ind in indicators:
            try:
                results[ind] = self.get_latest(ind)
            except Exception as e:
                results[ind] = None
        return results

    def get_oil_prices(self, months: int = 6) -> pd.DataFrame:
        """WTI/Brent 유가 시계열"""
        wti = self.get_series("wti", months)
        brent = self.get_series("brent", months)

        df = pd.merge(
            wti.rename(columns={"value": "wti"}),
            brent.rename(columns={"value": "brent"}),
            on="date",
            how="outer",
        ).sort_values("date")
        return df

    def get_commodity_prices(self, months: int = 6) -> pd.DataFrame:
        """주요 곡물 가격 시계열"""
        dfs = {}
        for crop in ["wheat", "corn", "soybean"]:
            try:
                s = self.get_series(crop, months)
                dfs[crop] = s.rename(columns={"value": crop})
            except Exception:
                pass

        if not dfs:
            return pd.DataFrame()

        result = None
        for name, df in dfs.items():
            if result is None:
                result = df
            else:
                result = pd.merge(result, df, on="date", how="outer")
        return result.sort_values("date")
