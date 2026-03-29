"""수동 입력 데이터 로더"""

from utils.helpers import load_yaml


class ManualLoader:
    """YAML 기반 수동 데이터 로더"""

    def __init__(self, filepath: str = "config/manual_data.yaml"):
        self.filepath = filepath
        self._data = None

    @property
    def data(self) -> dict:
        if self._data is None:
            self._data = load_yaml(self.filepath)
        return self._data

    def reload(self):
        """데이터 리로드"""
        self._data = None

    def get_energy_data(self) -> dict:
        return self.data.get("energy", {})

    def get_agriculture_data(self) -> dict:
        return self.data.get("agriculture", {})

    def get_sector_data(self) -> dict:
        return self.data.get("industry", {}).get("sectors", {})

    def get_finance_data(self) -> dict:
        return self.data.get("finance", {})

    def get_labor_data(self) -> dict:
        return self.data.get("labor", {})

    def get_policy_data(self) -> dict:
        return self.data.get("policy", {})

    def get_macro_baseline(self) -> dict:
        return self.data.get("macro_baseline", {})

    def get_oil_import_by_country(self) -> dict:
        return self.get_energy_data().get("korea_oil_import", {}).get("by_country_pct", {})

    def get_power_mix(self) -> dict:
        return self.get_energy_data().get("power_generation_mix_pct", {})

    def get_grain_import(self) -> dict:
        return self.get_agriculture_data().get("korea_grain_import", {})

    def get_corporate_debt(self) -> dict:
        return self.get_finance_data().get("corporate_debt", {})
