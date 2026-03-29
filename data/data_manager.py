"""K-RESA 데이터 통합 관리자"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Any

from data.collectors.fred_api import FredCollector
from data.collectors.bok_ecos import BokEcosCollector
from data.collectors.manual_loader import ManualLoader
from utils.helpers import load_yaml, get_api_key


class DataManager:
    """모든 데이터 소스를 통합 관리"""

    def __init__(self):
        self.settings = load_yaml("config/settings.yaml")
        self.manual = ManualLoader()
        self._fred = None
        self._bok = None
        self._market_data = {}
        self._macro_data = {}

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
        indicators = {}

        # API 데이터 시도 → 실패 시 수동 데이터 대체
        try:
            indicators["oil_wti"] = self.fred.get_latest("wti")
            indicators["oil_brent"] = self.fred.get_latest("brent")
            indicators["usd_krw"] = self.fred.get_latest("usd_krw")
            indicators["wheat"] = self.fred.get_latest("wheat")
            indicators["corn"] = self.fred.get_latest("corn")
        except Exception:
            baseline = self.manual.get_macro_baseline()
            indicators["oil_wti"] = 72.0
            indicators["oil_brent"] = 76.0
            indicators["usd_krw"] = baseline.get("exchange_rate_usd_krw", 1450)
            indicators["wheat"] = 650.0
            indicators["corn"] = 450.0

        try:
            bok_data = self.bok.get_key_indicators()
            # None 값은 제외하고 업데이트
            indicators.update({k: v for k, v in bok_data.items() if v is not None})
        except Exception:
            pass

        # 수동 데이터로 누락값 보완
        baseline = self.manual.get_macro_baseline()
        defaults = {
            "cpi_yoy": baseline.get("cpi_yoy_pct", 2.1),
            "ppi_yoy": baseline.get("ppi_yoy_pct", 1.8),
            "gdp_growth": baseline.get("gdp_growth_yoy_pct", 1.8),
            "unemployment": baseline.get("unemployment_pct", 2.8),
            "base_rate": baseline.get("base_rate_pct", 2.75),
            "trade_balance": baseline.get("trade_balance_billion_usd", 4.2),
            "credit_spread": baseline.get("credit_spread_bp", 85),
        }
        for k, v in defaults.items():
            if k not in indicators or indicators[k] is None:
                indicators[k] = v

        return indicators

    def get_time_series(self, indicator: str, months: int = 6) -> pd.DataFrame:
        """특정 지표의 시계열 데이터 반환"""
        try:
            return self.fred.get_series(indicator, months=months)
        except Exception:
            # 시계열 불가 시 단일값 기반 더미 생성
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
        """산업별 구조 데이터"""
        return self.manual.get_sector_data()

    def get_energy_data(self) -> dict:
        """에너지 부문 데이터"""
        return self.manual.get_energy_data()

    def get_agriculture_data(self) -> dict:
        """농산물 부문 데이터"""
        return self.manual.get_agriculture_data()

    def get_finance_data(self) -> dict:
        """금융 부문 데이터"""
        return self.manual.get_finance_data()

    def get_policy_data(self) -> dict:
        """정책 변수 데이터"""
        return self.manual.get_policy_data()

    def get_all_baseline(self) -> dict:
        """분석에 필요한 전체 기준 데이터셋 반환"""
        return {
            "indicators": self.get_current_indicators(),
            "sectors": self.get_sector_data(),
            "energy": self.get_energy_data(),
            "agriculture": self.get_agriculture_data(),
            "finance": self.get_finance_data(),
            "policy": self.get_policy_data(),
        }
