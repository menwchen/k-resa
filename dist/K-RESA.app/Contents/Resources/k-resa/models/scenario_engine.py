"""시나리오 구성/재구성 엔진"""

from dataclasses import dataclass, field
from utils.constants import SHOCK_LEVELS, COMPOUND_INTERACTION, SCENARIO_PRIORS


@dataclass
class ShockParams:
    """개별 충격 파라미터"""
    oil_price_change_pct: float = 0.0       # 유가 변동 (%)
    lng_price_change_pct: float = 0.0       # LNG 가격 변동 (%)
    electricity_cost_change_pct: float = 0.0 # 전력비용 변동 (%)
    grain_price_change_pct: float = 0.0     # 곡물가 변동 (%)
    fertilizer_price_change_pct: float = 0.0 # 비료가 변동 (%)
    feed_price_change_pct: float = 0.0      # 사료가 변동 (%)
    credit_spread_change_bp: float = 0.0    # 신용스프레드 변동 (bp)
    exchange_rate_change_pct: float = 0.0   # 환율 변동 (%)
    interest_rate_change_pct: float = 0.0   # 금리 변동 (%p)


@dataclass
class Scenario:
    """시나리오 정의"""
    name: str
    description: str
    crisis_type: str                          # energy / agri / financial / compound
    severity: str = "moderate"                # mild / moderate / severe
    shock: ShockParams = field(default_factory=ShockParams)
    probability: float = 0.10
    sub_scenarios: list = field(default_factory=list)  # 복합 시나리오용


# ─── 프리셋 시나리오 정의 ───

ENERGY_PRESETS = {
    "mild": ShockParams(
        oil_price_change_pct=20,
        lng_price_change_pct=15,
        electricity_cost_change_pct=8,
        exchange_rate_change_pct=3,
    ),
    "moderate": ShockParams(
        oil_price_change_pct=50,
        lng_price_change_pct=40,
        electricity_cost_change_pct=20,
        exchange_rate_change_pct=8,
    ),
    "severe": ShockParams(
        oil_price_change_pct=100,
        lng_price_change_pct=80,
        electricity_cost_change_pct=45,
        exchange_rate_change_pct=15,
    ),
}

AGRI_PRESETS = {
    "mild": ShockParams(
        grain_price_change_pct=15,
        fertilizer_price_change_pct=10,
        feed_price_change_pct=12,
    ),
    "moderate": ShockParams(
        grain_price_change_pct=40,
        fertilizer_price_change_pct=30,
        feed_price_change_pct=35,
    ),
    "severe": ShockParams(
        grain_price_change_pct=80,
        fertilizer_price_change_pct=60,
        feed_price_change_pct=70,
    ),
}

FINANCIAL_PRESETS = {
    "mild": ShockParams(
        credit_spread_change_bp=50,
        exchange_rate_change_pct=5,
        interest_rate_change_pct=0.25,
    ),
    "moderate": ShockParams(
        credit_spread_change_bp=150,
        exchange_rate_change_pct=12,
        interest_rate_change_pct=0.75,
    ),
    "severe": ShockParams(
        credit_spread_change_bp=350,
        exchange_rate_change_pct=25,
        interest_rate_change_pct=1.5,
    ),
}


class ScenarioEngine:
    """시나리오 구성 및 관리 엔진"""

    PRESETS = {
        "energy_crisis": ENERGY_PRESETS,
        "agri_crisis": AGRI_PRESETS,
        "financial_stress": FINANCIAL_PRESETS,
    }

    def create_preset(self, crisis_type: str, severity: str) -> Scenario:
        """프리셋 시나리오 생성"""
        labels = {"mild": "경미", "moderate": "중간", "severe": "심각"}
        type_labels = {
            "energy_crisis": "에너지 위기",
            "agri_crisis": "농산물 위기",
            "financial_stress": "금융 불안",
        }

        preset = self.PRESETS[crisis_type][severity]
        prob = SCENARIO_PRIORS[crisis_type][severity]

        return Scenario(
            name=f"{type_labels[crisis_type]} ({labels[severity]})",
            description=f"{type_labels[crisis_type]} - {labels[severity]} 수준 시나리오",
            crisis_type=crisis_type,
            severity=severity,
            shock=preset,
            probability=prob,
        )

    def create_custom(self, name: str, shock_params: dict) -> Scenario:
        """사용자 정의 시나리오 생성"""
        shock = ShockParams(**shock_params)
        return Scenario(
            name=name,
            description=f"사용자 정의 시나리오: {name}",
            crisis_type="custom",
            shock=shock,
            probability=0.10,
        )

    def create_compound(self, scenarios: list[Scenario]) -> Scenario:
        """복합 시나리오 생성 (상호작용 효과 포함)"""
        combined_shock = ShockParams()
        types = tuple(sorted(s.crisis_type for s in scenarios))

        # 기본 충격 합산
        for s in scenarios:
            for f in ShockParams.__dataclass_fields__:
                current = getattr(combined_shock, f)
                addition = getattr(s.shock, f)
                setattr(combined_shock, f, current + addition)

        # 상호작용 계수 적용
        interaction = COMPOUND_INTERACTION.get(types, 1.0)
        for f in ShockParams.__dataclass_fields__:
            val = getattr(combined_shock, f)
            setattr(combined_shock, f, val * interaction)

        # 복합 확률 = 개별 확률의 곱 (독립 가정) × 상관 보정
        compound_prob = 1.0
        for s in scenarios:
            compound_prob *= s.probability
        compound_prob *= (interaction ** 0.5)  # 상관 보정

        names = " + ".join(s.name for s in scenarios)
        return Scenario(
            name=f"복합: {names}",
            description=f"복합 위기 시나리오 (상호작용 계수: {interaction:.2f})",
            crisis_type="compound",
            severity="compound",
            shock=combined_shock,
            probability=min(compound_prob, 0.5),
            sub_scenarios=scenarios,
        )

    def get_all_presets(self) -> list[Scenario]:
        """모든 프리셋 시나리오 반환"""
        result = []
        for crisis_type in self.PRESETS:
            for severity in ["mild", "moderate", "severe"]:
                result.append(self.create_preset(crisis_type, severity))
        return result

    def scenario_to_dict(self, scenario: Scenario) -> dict:
        """시나리오를 딕셔너리로 변환 (시각화용)"""
        shock_dict = {}
        for f in ShockParams.__dataclass_fields__:
            val = getattr(scenario.shock, f)
            if val != 0:
                shock_dict[f] = val

        return {
            "name": scenario.name,
            "description": scenario.description,
            "crisis_type": scenario.crisis_type,
            "severity": scenario.severity,
            "probability": scenario.probability,
            "shocks": shock_dict,
        }
