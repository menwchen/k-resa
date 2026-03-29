"""K-RESA 데이터 통합 관리자"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Any

from data.collectors.fred_api import FredCollector
from data.collectors.bok_ecos import BokEcosCollector
from data.collectors.manual_loader import ManualLoader
from utils.helpers import get_api_key


class DataManager:
    """모든 데이터 소스를 통합 관리"""

    # API 접근 불가 시 사용할 하드코딩 기본값
    FALLBACK = {
        "oil_wti": 72.0,
        "oil_brent": 76.0,
        "usd_krw": 1450.0,
        "wheat": 650.0,
        "corn": 450.0,
        "cpi_yoy": 2.1,
        "ppi_yoy": 1.8,
        "gdp_growth": 1.8,
        "unemployment": 2.8,
        "base_rate": 2.75,
        "trade_balance": 4.2,
        "credit_spread": 85,
        "current_account": 8.0,
    }

    def __init__(self):
        self.manual = ManualLoader()
        self._fred = None
        self._bok = None

    @property
    def fred(self) -> FredCollector:
        if self._fred is None:
            api_key = get_api_key("fred")
            self._fred = FredCollector(api_key)
        return self._fred

    @property
    def bok(self) -> BokEcosCollector:
        if self._bok is None:
            api_key = get_api_key("bok_ecos")
            self._bok = BokEcosCollector(api_key)
        return self._bok

    def get_current_indicators(self) -> dict:
        """현재 주요 지표를 수집하여 반환"""
        # 1. 하드코딩 기본값으로 시작
        indicators = dict(self.FALLBACK)

        # 2. 수동 데이터(YAML)로 덮어쓰기
        try:
            baseline = self.manual.get_macro_baseline()
            policy = self.manual.get_policy_data()
            yaml_map = {
                "cpi_yoy": baseline.get("cpi_yoy_pct"),
                "ppi_yoy": baseline.get("ppi_yoy_pct"),
                "gdp_growth": baseline.get("gdp_growth_yoy_pct"),
                "unemployment": baseline.get("unemployment_pct"),
                "usd_krw": baseline.get("exchange_rate_usd_krw"),
                "trade_balance": baseline.get("trade_balance_billion_usd"),
                "credit_spread": baseline.get("credit_spread_bp"),
                "base_rate": policy.get("base_rate_pct"),
            }
            for k, v in yaml_map.items():
                if v is not None:
                    indicators[k] = v
        except Exception:
            pass

        # 3. FRED API (유가, 환율, 곡물)
        try:
            indicators["oil_wti"] = self.fred.get_latest("wti")
            indicators["oil_brent"] = self.fred.get_latest("brent")
            indicators["usd_krw"] = self.fred.get_latest("usd_krw")
            indicators["wheat"] = self.fred.get_latest("wheat")
            indicators["corn"] = self.fred.get_latest("corn")
        except Exception:
            pass

        # 4. 한국은행 ECOS API
        try:
            bok_data = self.bok.get_key_indicators()
            for k, v in bok_data.items():
                if v is not None:
                    indicators[k] = v
        except Exception:
            pass

        return indicators

    def get_time_series(self, indicator: str, months: int = 6) -> pd.DataFrame:
        """특정 지표의 시계열 데이터 반환"""
        try:
            return self.fred.get_series(indicator, months=months)
        except Exception:
            current = self.get_current_indicators().get(indicator, 100)
            dates = pd.date_range(
                end=datetime.now(), periods=months * 22, freq="B"
            )
            noise = pd.Series(
                [current * (1 + (i % 5 - 2) * 0.005) for i in range(len(dates))],
                index=dates,
            )
            return pd.DataFrame({"date": dates, "value": noise.values})

    def get_sector_data(self) -> dict:
        return self.manual.get_sector_data()

    def get_energy_data(self) -> dict:
        return self.manual.get_energy_data()

    def get_agriculture_data(self) -> dict:
        return self.manual.get_agriculture_data()

    def get_finance_data(self) -> dict:
        return self.manual.get_finance_data()

    def get_policy_data(self) -> dict:
        return self.manual.get_policy_data()

    def get_all_baseline(self) -> dict:
        return {
            "indicators": self.get_current_indicators(),
            "sectors": self.get_sector_data(),
            "energy": self.get_energy_data(),
            "agriculture": self.get_agriculture_data(),
            "finance": self.get_finance_data(),
            "policy": self.get_policy_data(),
        }
