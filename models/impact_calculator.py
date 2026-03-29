"""파급효과 계산 엔진"""

from dataclasses import dataclass
from models.scenario_engine import Scenario, ShockParams
from utils.constants import (
    ENERGY_PASSTHROUGH, AGRI_PASSTHROUGH, FX_PASSTHROUGH,
    CPI_WEIGHTS, SECTOR_NAMES_KR,
)


@dataclass
class ImpactResult:
    """파급효과 계산 결과"""
    gdp_impact_pct: float = 0.0
    cpi_impact_pct: float = 0.0
    ppi_impact_pct: float = 0.0
    trade_balance_impact_billion_usd: float = 0.0
    unemployment_impact_pct: float = 0.0
    exchange_rate_impact_pct: float = 0.0
    sector_impacts: dict = None
    transmission_paths: list = None

    def __post_init__(self):
        if self.sector_impacts is None:
            self.sector_impacts = {}
        if self.transmission_paths is None:
            self.transmission_paths = []


class ImpactCalculator:
    """외부 충격의 한국 경제 파급효과 계산"""

    def __init__(self, baseline: dict):
        """
        baseline: DataManager.get_all_baseline() 의 반환값
        """
        self.indicators = baseline.get("indicators", {})
        self.sectors = baseline.get("sectors", {})
        self.energy = baseline.get("energy", {})
        self.agriculture = baseline.get("agriculture", {})
        self.finance = baseline.get("finance", {})
        self.policy = baseline.get("policy", {})

    def calculate(self, scenario: Scenario) -> ImpactResult:
        """시나리오의 전체 파급효과 계산"""
        shock = scenario.shock
        result = ImpactResult()
        paths = []

        # 1. 에너지 경로
        energy_cpi, energy_ppi, energy_paths = self._calc_energy_impact(shock)
        result.cpi_impact_pct += energy_cpi
        result.ppi_impact_pct += energy_ppi
        paths.extend(energy_paths)

        # 2. 농산물 경로
        agri_cpi, agri_paths = self._calc_agri_impact(shock)
        result.cpi_impact_pct += agri_cpi
        paths.extend(agri_paths)

        # 3. 환율 경로
        fx_cpi, fx_ppi, fx_paths = self._calc_fx_impact(shock)
        result.cpi_impact_pct += fx_cpi
        result.ppi_impact_pct += fx_ppi
        paths.extend(fx_paths)

        # 4. 금융 경로
        fin_gdp, fin_paths = self._calc_financial_impact(shock)
        result.gdp_impact_pct += fin_gdp
        paths.extend(fin_paths)

        # 5. 산업별 영향
        result.sector_impacts = self._calc_sector_impacts(shock)

        # 6. GDP 총 영향 (산업 가중 합산)
        gdp_from_sectors = sum(
            self.sectors.get(s, {}).get("gdp_share_pct", 0) / 100 * imp.get("total_impact_pct", 0) / 100
            for s, imp in result.sector_impacts.items()
        )
        result.gdp_impact_pct += gdp_from_sectors * -100  # 음수 = 성장률 하락

        # 7. 무역수지 영향
        result.trade_balance_impact_billion_usd = self._calc_trade_impact(shock)

        # 8. 실업 영향 (GDP 대비 오쿤 법칙 근사)
        result.unemployment_impact_pct = result.gdp_impact_pct * -0.4

        # 9. 환율 영향
        result.exchange_rate_impact_pct = shock.exchange_rate_change_pct

        result.transmission_paths = paths
        return result

    def _calc_energy_impact(self, shock: ShockParams) -> tuple:
        """에너지 충격 → CPI/PPI 영향"""
        paths = []
        oil_pct = shock.oil_price_change_pct / 100

        # 유가 → PPI
        ppi_direct = oil_pct * ENERGY_PASSTHROUGH["oil_to_ppi"] * 100
        paths.append({
            "from": "유가", "to": "PPI", "value": ppi_direct,
            "mechanism": f"유가 {shock.oil_price_change_pct:+.0f}% → PPI {ppi_direct:+.2f}%p"
        })

        # 유가 → CPI (직접)
        cpi_direct = oil_pct * ENERGY_PASSTHROUGH["oil_to_cpi"] * 100
        paths.append({
            "from": "유가", "to": "CPI(직접)", "value": cpi_direct,
            "mechanism": f"유가 → 휘발유/경유 → CPI {cpi_direct:+.2f}%p"
        })

        # PPI → CPI (간접)
        cpi_indirect = ppi_direct / 100 * ENERGY_PASSTHROUGH["ppi_to_cpi"] * 100
        paths.append({
            "from": "PPI", "to": "CPI(간접)", "value": cpi_indirect,
            "mechanism": f"PPI → 소비재가격 → CPI {cpi_indirect:+.2f}%p"
        })

        # LNG → 전력요금
        lng_pct = shock.lng_price_change_pct / 100
        elec_impact = lng_pct * ENERGY_PASSTHROUGH["lng_to_electricity"]
        elec_cpi = elec_impact * CPI_WEIGHTS["energy"]["electricity"] / 1000 * 100
        paths.append({
            "from": "LNG가격", "to": "전력요금→CPI", "value": elec_cpi,
            "mechanism": f"LNG {shock.lng_price_change_pct:+.0f}% → 전력 → CPI {elec_cpi:+.2f}%p"
        })

        total_cpi = cpi_direct + cpi_indirect + elec_cpi
        total_ppi = ppi_direct

        return total_cpi, total_ppi, paths

    def _calc_agri_impact(self, shock: ShockParams) -> tuple:
        """농산물 충격 → CPI 영향"""
        paths = []
        grain_pct = shock.grain_price_change_pct / 100

        # 곡물 → 사료 → 육류
        feed_impact = grain_pct * AGRI_PASSTHROUGH["grain_to_feed"]
        meat_impact = feed_impact * AGRI_PASSTHROUGH["feed_to_meat"]
        meat_cpi = meat_impact * CPI_WEIGHTS["food"]["meat"] / 1000 * 100
        paths.append({
            "from": "곡물가", "to": "사료→육류→CPI", "value": meat_cpi,
            "mechanism": f"곡물 {shock.grain_price_change_pct:+.0f}% → 사료 → 육류 CPI {meat_cpi:+.2f}%p"
        })

        # 곡물 → 가공식품
        processed_impact = grain_pct * AGRI_PASSTHROUGH["grain_to_processed"]
        processed_cpi = processed_impact * CPI_WEIGHTS["food"]["processed_food"] / 1000 * 100
        paths.append({
            "from": "곡물가", "to": "가공식품→CPI", "value": processed_cpi,
            "mechanism": f"곡물 → 가공식품 CPI {processed_cpi:+.2f}%p"
        })

        # 비료 → 채소/과일
        fert_pct = shock.fertilizer_price_change_pct / 100
        veg_impact = fert_pct * AGRI_PASSTHROUGH["fertilizer_to_crop"]
        veg_cpi = veg_impact * (CPI_WEIGHTS["food"]["vegetables"] + CPI_WEIGHTS["food"]["fruits"]) / 1000 * 100
        paths.append({
            "from": "비료가", "to": "채소/과일→CPI", "value": veg_cpi,
            "mechanism": f"비료 {shock.fertilizer_price_change_pct:+.0f}% → 채소/과일 CPI {veg_cpi:+.2f}%p"
        })

        total_cpi = meat_cpi + processed_cpi + veg_cpi
        return total_cpi, paths

    def _calc_fx_impact(self, shock: ShockParams) -> tuple:
        """환율 충격 → 수입물가 → PPI → CPI"""
        paths = []
        fx_pct = shock.exchange_rate_change_pct / 100

        import_price = fx_pct * FX_PASSTHROUGH["to_import_price"] * 100
        ppi = fx_pct * FX_PASSTHROUGH["to_ppi"] * 100
        cpi = fx_pct * FX_PASSTHROUGH["to_cpi"] * 100

        paths.append({
            "from": "환율", "to": "수입물가→PPI→CPI", "value": cpi,
            "mechanism": f"환율 {shock.exchange_rate_change_pct:+.0f}% → 수입물가 {import_price:+.1f}% → CPI {cpi:+.2f}%p"
        })

        return cpi, ppi, paths

    def _calc_financial_impact(self, shock: ShockParams) -> tuple:
        """금융 충격 → GDP 영향"""
        paths = []

        # 신용스프레드 확대 → 기업 투자 위축
        spread_bp = shock.credit_spread_change_bp
        investment_impact = -spread_bp / 100 * 0.3  # 100bp당 투자 0.3% 감소
        gdp_from_investment = investment_impact * 0.30  # 투자의 GDP 비중 ~30%

        paths.append({
            "from": "신용스프레드", "to": "기업투자→GDP", "value": gdp_from_investment,
            "mechanism": f"스프레드 {spread_bp:+.0f}bp → 투자 {investment_impact:+.1f}% → GDP {gdp_from_investment:+.2f}%p"
        })

        # 금리 상승 → 소비 위축
        rate_pct = shock.interest_rate_change_pct
        consumption_impact = -rate_pct * 0.5  # 1%p 인상당 소비 0.5% 감소
        gdp_from_consumption = consumption_impact * 0.50  # 소비의 GDP 비중 ~50%

        paths.append({
            "from": "금리", "to": "가계소비→GDP", "value": gdp_from_consumption,
            "mechanism": f"금리 {rate_pct:+.2f}%p → 소비 {consumption_impact:+.1f}% → GDP {gdp_from_consumption:+.2f}%p"
        })

        total_gdp = gdp_from_investment + gdp_from_consumption
        return total_gdp, paths

    def _calc_sector_impacts(self, shock: ShockParams) -> dict:
        """산업별 영향 계산"""
        results = {}
        for sector, info in self.sectors.items():
            energy_hit = (
                info.get("energy_intensity", 0) *
                shock.oil_price_change_pct / 100 * 50  # 에너지 비용 증가분의 50% 흡수
            )
            import_hit = (
                info.get("import_dependency_pct", 0) / 100 *
                shock.exchange_rate_change_pct / 100 * 30
            )
            finance_hit = (
                shock.credit_spread_change_bp / 1000 *
                (1 - info.get("export_share_pct", 0) / 100) * 10
            )

            total = energy_hit + import_hit + finance_hit
            results[sector] = {
                "name_kr": SECTOR_NAMES_KR.get(sector, sector),
                "energy_impact_pct": round(energy_hit, 2),
                "import_impact_pct": round(import_hit, 2),
                "finance_impact_pct": round(finance_hit, 2),
                "total_impact_pct": round(total, 2),
                "employment_risk": "high" if total > 5 else "medium" if total > 2 else "low",
            }
        return results

    def _calc_trade_impact(self, shock: ShockParams) -> float:
        """무역수지 영향 (십억 달러)"""
        baseline_tb = self.indicators.get("trade_balance") or 4.2

        # 수입비용 증가
        oil_import_cost = shock.oil_price_change_pct / 100 * 8.5  # 연간 유류 수입 ~85억달러/월
        grain_import_cost = shock.grain_price_change_pct / 100 * 1.2  # 곡물 수입 ~12억달러/월
        fx_cost = shock.exchange_rate_change_pct / 100 * baseline_tb * 0.3

        import_increase = oil_import_cost + grain_import_cost + fx_cost

        # 수출 변화 (환율 약세 → 수출 경쟁력 일부 개선)
        export_fx_benefit = shock.exchange_rate_change_pct / 100 * 2.0

        return round(-(import_increase - export_fx_benefit), 2)

    def result_to_dict(self, result: ImpactResult) -> dict:
        """결과를 딕셔너리로 변환"""
        return {
            "gdp_impact_pct": round(result.gdp_impact_pct, 2),
            "cpi_impact_pct": round(result.cpi_impact_pct, 2),
            "ppi_impact_pct": round(result.ppi_impact_pct, 2),
            "trade_balance_impact_billion_usd": result.trade_balance_impact_billion_usd,
            "unemployment_impact_pct": round(result.unemployment_impact_pct, 2),
            "exchange_rate_impact_pct": round(result.exchange_rate_impact_pct, 2),
            "sector_impacts": result.sector_impacts,
            "transmission_paths": result.transmission_paths,
        }
