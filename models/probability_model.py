"""확률 모델 (베이지안 업데이트 + Monte Carlo)"""

import numpy as np
from dataclasses import dataclass
from models.scenario_engine import Scenario, ScenarioEngine
from utils.constants import SCENARIO_PRIORS, COMPOUND_INTERACTION


@dataclass
class ProbabilityResult:
    """확률 분석 결과"""
    prior: float
    posterior: float
    evidence_factors: list
    confidence_interval: tuple  # (lower, upper)
    monte_carlo_mean: float
    monte_carlo_std: float
    distribution: np.ndarray = None


class ProbabilityModel:
    """베이지안 확률 업데이트 및 Monte Carlo 시뮬레이션"""

    def __init__(self, n_simulations: int = 10000, seed: int = 42):
        self.n_sim = n_simulations
        self.rng = np.random.default_rng(seed)

    def bayesian_update(self, prior: float, evidence: list[dict]) -> ProbabilityResult:
        """
        베이지안 확률 업데이트

        evidence: [{"name": "유가 상승 추세", "likelihood_ratio": 1.5}, ...]
        likelihood_ratio > 1: 시나리오 발생 가능성 높임
        likelihood_ratio < 1: 시나리오 발생 가능성 낮춤
        """
        posterior = prior

        for ev in evidence:
            lr = ev.get("likelihood_ratio", 1.0)
            # 베이즈 정리: P(H|E) = P(E|H)*P(H) / P(E)
            # 단순화: odds_posterior = odds_prior * likelihood_ratio
            odds = posterior / (1 - posterior + 1e-10)
            odds *= lr
            posterior = odds / (1 + odds)

        posterior = np.clip(posterior, 0.001, 0.999)

        return ProbabilityResult(
            prior=prior,
            posterior=posterior,
            evidence_factors=evidence,
            confidence_interval=self._wilson_interval(posterior),
            monte_carlo_mean=posterior,
            monte_carlo_std=0.0,
        )

    def monte_carlo_simulation(self, scenario: Scenario,
                                shock_std_pct: float = 20.0) -> ProbabilityResult:
        """
        Monte Carlo 시뮬레이션으로 불확실성 범위 산출

        shock_std_pct: 충격 변수의 표준편차 (기본값의 %)
        """
        base_prob = scenario.probability

        # 충격 변수들에 노이즈를 추가하여 시뮬레이션
        simulated_probs = []
        for _ in range(self.n_sim):
            noise = self.rng.normal(1.0, shock_std_pct / 100)
            adjusted_prob = base_prob * max(noise, 0.01)
            adjusted_prob = np.clip(adjusted_prob, 0.001, 0.999)
            simulated_probs.append(adjusted_prob)

        dist = np.array(simulated_probs)
        mean = np.mean(dist)
        std = np.std(dist)
        ci_low = np.percentile(dist, 2.5)
        ci_high = np.percentile(dist, 97.5)

        return ProbabilityResult(
            prior=base_prob,
            posterior=mean,
            evidence_factors=[],
            confidence_interval=(ci_low, ci_high),
            monte_carlo_mean=mean,
            monte_carlo_std=std,
            distribution=dist,
        )

    def compound_probability(self, scenarios: list[Scenario],
                              correlation: float = 0.3) -> float:
        """
        복합 시나리오 확률 계산 (상관관계 고려)

        독립 가정: P(A∩B) = P(A) * P(B)
        상관 보정: P(A∩B) ≈ P(A) * P(B) * (1 + corr * sqrt(P(A)*P(B)))
        """
        if not scenarios:
            return 0.0

        prob = 1.0
        for s in scenarios:
            prob *= s.probability

        # 상관 보정
        avg_prob = np.mean([s.probability for s in scenarios])
        correction = 1 + correlation * np.sqrt(avg_prob)
        prob *= correction

        # 상호작용 계수 추가 적용
        types = tuple(sorted(s.crisis_type for s in scenarios))
        interaction = COMPOUND_INTERACTION.get(types, 1.0)
        prob *= (interaction ** 0.3)

        return min(prob, 0.95)

    def scenario_probability_table(self, engine: ScenarioEngine,
                                    evidence: list[dict] = None) -> list[dict]:
        """
        전체 시나리오 확률 테이블 생성

        Returns: [{"scenario": name, "prior": p, "posterior": p, ...}, ...]
        """
        if evidence is None:
            evidence = []

        results = []
        for scenario in engine.get_all_presets():
            mc = self.monte_carlo_simulation(scenario)

            if evidence:
                bayes = self.bayesian_update(scenario.probability, evidence)
                posterior = bayes.posterior
            else:
                posterior = scenario.probability

            results.append({
                "scenario": scenario.name,
                "crisis_type": scenario.crisis_type,
                "severity": scenario.severity,
                "prior": scenario.probability,
                "posterior": round(posterior, 4),
                "mc_mean": round(mc.monte_carlo_mean, 4),
                "mc_std": round(mc.monte_carlo_std, 4),
                "ci_low": round(mc.confidence_interval[0], 4),
                "ci_high": round(mc.confidence_interval[1], 4),
            })

        return sorted(results, key=lambda x: x["posterior"], reverse=True)

    def impact_distribution(self, scenario: Scenario,
                             calculator,
                             baseline: dict,
                             n_samples: int = 1000) -> dict:
        """충격의 영향 분포 시뮬레이션"""
        from models.scenario_engine import ShockParams

        gdp_impacts = []
        cpi_impacts = []

        for _ in range(n_samples):
            # 충격 변수에 노이즈 추가
            noisy_params = {}
            for f in ShockParams.__dataclass_fields__:
                base_val = getattr(scenario.shock, f)
                if base_val != 0:
                    noise = self.rng.normal(1.0, 0.2)
                    noisy_params[f] = base_val * max(noise, 0)
                else:
                    noisy_params[f] = 0

            noisy_scenario = Scenario(
                name=scenario.name,
                description=scenario.description,
                crisis_type=scenario.crisis_type,
                shock=ShockParams(**noisy_params),
                probability=scenario.probability,
            )

            result = calculator.calculate(noisy_scenario)
            gdp_impacts.append(result.gdp_impact_pct)
            cpi_impacts.append(result.cpi_impact_pct)

        return {
            "gdp": {
                "mean": np.mean(gdp_impacts),
                "std": np.std(gdp_impacts),
                "p5": np.percentile(gdp_impacts, 5),
                "p95": np.percentile(gdp_impacts, 95),
                "distribution": gdp_impacts,
            },
            "cpi": {
                "mean": np.mean(cpi_impacts),
                "std": np.std(cpi_impacts),
                "p5": np.percentile(cpi_impacts, 5),
                "p95": np.percentile(cpi_impacts, 95),
                "distribution": cpi_impacts,
            },
        }

    @staticmethod
    def _wilson_interval(p: float, n: int = 100, z: float = 1.96) -> tuple:
        """윌슨 신뢰구간"""
        denominator = 1 + z**2 / n
        center = (p + z**2 / (2 * n)) / denominator
        margin = z * np.sqrt((p * (1 - p) + z**2 / (4 * n)) / n) / denominator
        return (max(0, center - margin), min(1, center + margin))
