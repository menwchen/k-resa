"""정책 대응 시뮬레이터"""

from dataclasses import dataclass, field
from models.impact_calculator import ImpactResult
from utils.constants import POLICY_EFFECTS


@dataclass
class PolicyAction:
    """개별 정책 행동"""
    name: str
    description: str
    policy_type: str  # monetary / fiscal / trade / energy
    magnitude: float  # 정책 강도
    unit: str

    # 효과
    gdp_effect_pct: float = 0.0
    cpi_effect_pct: float = 0.0
    exchange_rate_effect_pct: float = 0.0
    fiscal_cost_trillion_krw: float = 0.0
    lag_quarters: int = 0


@dataclass
class PolicyPackage:
    """정책 패키지 (복수 정책 조합)"""
    name: str
    actions: list = field(default_factory=list)
    total_gdp_effect_pct: float = 0.0
    total_cpi_effect_pct: float = 0.0
    total_fiscal_cost_trillion_krw: float = 0.0
    net_gdp_after_shock_pct: float = 0.0
    net_cpi_after_shock_pct: float = 0.0
    effectiveness_score: float = 0.0  # 비용 대비 효과


class PolicySimulator:
    """정책 대응 시뮬레이터"""

    # ─── 정책 도구 정의 ───
    POLICY_TOOLS = {
        "rate_hike": {
            "name": "기준금리 인상",
            "description": "한국은행 기준금리 인상 (0.25%p 단위)",
            "type": "monetary",
            "unit": "%p",
            "per_unit": {  # 0.25%p 인상당 효과
                "gdp_effect_pct": -0.12,
                "cpi_effect_pct": -0.08,
                "exchange_rate_effect_pct": -1.5,
                "fiscal_cost_trillion_krw": 0,
                "lag_quarters": 4,
            },
            "range": (0.25, 2.0),
            "step": 0.25,
        },
        "rate_cut": {
            "name": "기준금리 인하",
            "description": "한국은행 기준금리 인하 (0.25%p 단위)",
            "type": "monetary",
            "unit": "%p",
            "per_unit": {
                "gdp_effect_pct": 0.12,
                "cpi_effect_pct": 0.08,
                "exchange_rate_effect_pct": 1.5,
                "fiscal_cost_trillion_krw": 0,
                "lag_quarters": 4,
            },
            "range": (0.25, 1.5),
            "step": 0.25,
        },
        "oil_reserve": {
            "name": "전략비축유 방출",
            "description": "전략비축유 방출 (1000만 배럴 단위)",
            "type": "energy",
            "unit": "천만배럴",
            "per_unit": {
                "gdp_effect_pct": 0.02,
                "cpi_effect_pct": -0.15,
                "exchange_rate_effect_pct": -0.5,
                "fiscal_cost_trillion_krw": 0.8,
                "lag_quarters": 0,
            },
            "range": (1, 5),
            "step": 1,
        },
        "energy_subsidy": {
            "name": "에너지 보조금 확대",
            "description": "유류세 인하, 전기요금 보조 (조원 단위)",
            "type": "fiscal",
            "unit": "조원",
            "per_unit": {
                "gdp_effect_pct": 0.03,
                "cpi_effect_pct": -0.12,
                "exchange_rate_effect_pct": 0.2,
                "fiscal_cost_trillion_krw": 1.0,
                "lag_quarters": 0,
            },
            "range": (1, 15),
            "step": 1,
        },
        "food_tariff_cut": {
            "name": "식품 관세 인하",
            "description": "수입 농산물 관세 인하 (5%p 단위)",
            "type": "trade",
            "unit": "%p",
            "per_unit": {
                "gdp_effect_pct": 0.01,
                "cpi_effect_pct": -0.08,
                "exchange_rate_effect_pct": 0.0,
                "fiscal_cost_trillion_krw": 0.5,
                "lag_quarters": 1,
            },
            "range": (5, 20),
            "step": 5,
        },
        "fiscal_expansion": {
            "name": "재정 지출 확대",
            "description": "추경 편성 / 경기부양 지출 (조원 단위)",
            "type": "fiscal",
            "unit": "조원",
            "per_unit": {
                "gdp_effect_pct": 0.04,
                "cpi_effect_pct": 0.02,
                "exchange_rate_effect_pct": 0.3,
                "fiscal_cost_trillion_krw": 1.0,
                "lag_quarters": 2,
            },
            "range": (5, 50),
            "step": 5,
        },
        "fx_intervention": {
            "name": "외환시장 개입",
            "description": "원화 방어를 위한 외환보유고 활용 (십억달러 단위)",
            "type": "monetary",
            "unit": "십억$",
            "per_unit": {
                "gdp_effect_pct": 0.0,
                "cpi_effect_pct": -0.03,
                "exchange_rate_effect_pct": -2.0,
                "fiscal_cost_trillion_krw": 0.0,  # 외환보유고 사용
                "lag_quarters": 0,
            },
            "range": (5, 30),
            "step": 5,
        },
    }

    def create_action(self, tool_key: str, magnitude: float) -> PolicyAction:
        """정책 행동 생성"""
        tool = self.POLICY_TOOLS[tool_key]
        per = tool["per_unit"]
        base_unit = tool["range"][0]  # 기본 단위
        scale = magnitude / base_unit

        return PolicyAction(
            name=tool["name"],
            description=f"{tool['description']} ({magnitude}{tool['unit']})",
            policy_type=tool["type"],
            magnitude=magnitude,
            unit=tool["unit"],
            gdp_effect_pct=round(per["gdp_effect_pct"] * scale, 3),
            cpi_effect_pct=round(per["cpi_effect_pct"] * scale, 3),
            exchange_rate_effect_pct=round(per["exchange_rate_effect_pct"] * scale, 3),
            fiscal_cost_trillion_krw=round(per["fiscal_cost_trillion_krw"] * scale, 2),
            lag_quarters=per["lag_quarters"],
        )

    def create_package(self, name: str, actions: list[PolicyAction]) -> PolicyPackage:
        """정책 패키지 생성"""
        pkg = PolicyPackage(name=name, actions=actions)

        for a in actions:
            pkg.total_gdp_effect_pct += a.gdp_effect_pct
            pkg.total_cpi_effect_pct += a.cpi_effect_pct
            pkg.total_fiscal_cost_trillion_krw += a.fiscal_cost_trillion_krw

        pkg.total_gdp_effect_pct = round(pkg.total_gdp_effect_pct, 3)
        pkg.total_cpi_effect_pct = round(pkg.total_cpi_effect_pct, 3)
        pkg.total_fiscal_cost_trillion_krw = round(pkg.total_fiscal_cost_trillion_krw, 2)

        return pkg

    def evaluate_against_shock(self, package: PolicyPackage,
                                shock_result: ImpactResult) -> PolicyPackage:
        """충격 대비 정책 효과 평가"""
        package.net_gdp_after_shock_pct = round(
            shock_result.gdp_impact_pct + package.total_gdp_effect_pct, 2
        )
        package.net_cpi_after_shock_pct = round(
            shock_result.cpi_impact_pct + package.total_cpi_effect_pct, 2
        )

        # 비용-효과 점수: GDP 개선 + CPI 억제 효과를 재정비용으로 나눔
        gdp_improvement = max(0, package.total_gdp_effect_pct - shock_result.gdp_impact_pct * 0.01)
        cpi_improvement = max(0, -package.total_cpi_effect_pct)
        total_improvement = gdp_improvement + cpi_improvement

        cost = max(package.total_fiscal_cost_trillion_krw, 0.1)
        package.effectiveness_score = round(total_improvement / cost * 10, 2)

        return package

    def preset_packages(self) -> list[dict]:
        """프리셋 정책 패키지"""
        return [
            {
                "name": "보수적 대응",
                "description": "소극적 대응: 소규모 보조금 + 관세 인하",
                "actions": [
                    ("energy_subsidy", 3),
                    ("food_tariff_cut", 5),
                ],
            },
            {
                "name": "균형적 대응",
                "description": "통화+재정 혼합: 비축유 방출 + 보조금 + 추경",
                "actions": [
                    ("oil_reserve", 2),
                    ("energy_subsidy", 5),
                    ("food_tariff_cut", 10),
                    ("fiscal_expansion", 15),
                ],
            },
            {
                "name": "적극적 대응",
                "description": "전방위 대응: 대규모 재정 + 통화 완화 + 외환개입",
                "actions": [
                    ("oil_reserve", 4),
                    ("energy_subsidy", 10),
                    ("food_tariff_cut", 15),
                    ("fiscal_expansion", 30),
                    ("rate_cut", 0.5),
                    ("fx_intervention", 15),
                ],
            },
        ]

    def build_preset_package(self, preset_name: str) -> PolicyPackage:
        """프리셋 패키지 빌드"""
        presets = {p["name"]: p for p in self.preset_packages()}
        preset = presets[preset_name]

        actions = [self.create_action(tool, mag) for tool, mag in preset["actions"]]
        return self.create_package(preset["name"], actions)

    def get_policy_tools_info(self) -> list[dict]:
        """정책 도구 정보 반환 (UI용)"""
        return [
            {
                "key": key,
                "name": tool["name"],
                "description": tool["description"],
                "type": tool["type"],
                "unit": tool["unit"],
                "range": tool["range"],
                "step": tool["step"],
            }
            for key, tool in self.POLICY_TOOLS.items()
        ]

    def package_to_dict(self, pkg: PolicyPackage) -> dict:
        """패키지를 딕셔너리로 변환"""
        return {
            "name": pkg.name,
            "total_gdp_effect_pct": pkg.total_gdp_effect_pct,
            "total_cpi_effect_pct": pkg.total_cpi_effect_pct,
            "total_fiscal_cost_trillion_krw": pkg.total_fiscal_cost_trillion_krw,
            "net_gdp_after_shock_pct": pkg.net_gdp_after_shock_pct,
            "net_cpi_after_shock_pct": pkg.net_cpi_after_shock_pct,
            "effectiveness_score": pkg.effectiveness_score,
            "actions": [
                {
                    "name": a.name,
                    "magnitude": a.magnitude,
                    "unit": a.unit,
                    "gdp_effect": a.gdp_effect_pct,
                    "cpi_effect": a.cpi_effect_pct,
                    "fiscal_cost": a.fiscal_cost_trillion_krw,
                    "lag_quarters": a.lag_quarters,
                }
                for a in pkg.actions
            ],
        }
