"""Tab 4: 확률 분석"""

import streamlit as st
import pandas as pd
from dashboard.components.charts import gauge_chart, distribution_chart, bar_chart
from dashboard.components.widgets import evidence_input
from models.scenario_engine import ScenarioEngine
from models.probability_model import ProbabilityModel


def render(data_manager):
    """확률 분석 렌더링"""
    st.header("🎲 확률 분석")
    st.caption("시나리오별 발생 확률 및 베이지안 업데이트")

    engine = ScenarioEngine()
    prob_model = ProbabilityModel(n_simulations=5000)

    # ─── 증거 입력 ───
    evidence = evidence_input(key_prefix="prob_")

    if evidence:
        st.info(f"📌 {len(evidence)}개 증거 반영 중")

    st.divider()

    # ─── 확률 테이블 ───
    st.subheader("📊 시나리오별 발생 확률")

    prob_table = prob_model.scenario_probability_table(engine, evidence)

    # 테이블 표시
    df = pd.DataFrame(prob_table)
    df_display = df.copy()
    df_display["prior"] = df_display["prior"].apply(lambda x: f"{x*100:.1f}%")
    df_display["posterior"] = df_display["posterior"].apply(lambda x: f"{x*100:.1f}%")
    df_display["ci"] = df_display.apply(
        lambda r: f"[{r['ci_low']*100:.1f}%, {r['ci_high']*100:.1f}%]", axis=1
    )
    df_display = df_display.rename(columns={
        "scenario": "시나리오",
        "prior": "사전확률",
        "posterior": "사후확률",
        "ci": "95% 신뢰구간",
    })

    st.dataframe(
        df_display[["시나리오", "사전확률", "사후확률", "95% 신뢰구간"]],
        key=None,
        hide_index=True,
    )

    st.divider()

    # ─── 게이지 차트 ───
    st.subheader("🔴 주요 시나리오 확률 게이지")

    # 상위 6개 시나리오
    top_scenarios = prob_table[:6]
    cols = st.columns(3)
    for i, s in enumerate(top_scenarios):
        with cols[i % 3]:
            fig = gauge_chart(s["posterior"], s["scenario"])
            st.plotly_chart(fig, key=None)

    st.divider()

    # ─── 사전/사후 확률 비교 ───
    if evidence:
        st.subheader("📈 베이지안 업데이트 효과")

        names = [s["scenario"] for s in prob_table]
        priors = [s["prior"] * 100 for s in prob_table]
        posteriors = [s["posterior"] * 100 for s in prob_table]
        changes = [p - q for p, q in zip(posteriors, priors)]

        fig = bar_chart(names, changes, "사후확률 - 사전확률 변화 (%p)")
        st.plotly_chart(fig, key=None)

        # 반영된 증거 목록
        st.markdown("**반영된 증거:**")
        for ev in evidence:
            lr = ev["likelihood_ratio"]
            direction = "↑ 상승" if lr > 1 else "↓ 하락"
            st.markdown(f"- {ev['name']} (우도비: {lr:.1f}, 확률 {direction})")

    st.divider()

    # ─── 복합 시나리오 확률 ───
    st.subheader("🔗 복합 시나리오 확률")

    compound_configs = [
        ("에너지 + 농산물", ["energy_crisis", "agri_crisis"]),
        ("에너지 + 금융", ["energy_crisis", "financial_stress"]),
        ("농산물 + 금융", ["agri_crisis", "financial_stress"]),
        ("3중 복합 위기", ["energy_crisis", "agri_crisis", "financial_stress"]),
    ]

    for severity in ["mild", "moderate", "severe"]:
        severity_kr = {"mild": "경미", "moderate": "중간", "severe": "심각"}[severity]
        st.markdown(f"**{severity_kr} 수준:**")

        cols = st.columns(len(compound_configs))
        for col, (name, types) in zip(cols, compound_configs):
            scenarios = [engine.create_preset(t, severity) for t in types]
            compound_prob = prob_model.compound_probability(scenarios)
            with col:
                st.metric(name, f"{compound_prob * 100:.2f}%")

    # ─── Monte Carlo 분포 ───
    st.divider()
    st.subheader("🎯 Monte Carlo 시뮬레이션")

    current_scenario = st.session_state.get("current_scenario")
    if current_scenario:
        mc_result = prob_model.monte_carlo_simulation(current_scenario)
        if mc_result.distribution is not None:
            fig = distribution_chart(
                (mc_result.distribution * 100).tolist(),
                f"{current_scenario.name} - 확률 분포",
                xlabel="발생 확률 (%)",
                ci=(mc_result.confidence_interval[0] * 100,
                    mc_result.confidence_interval[1] * 100),
            )
            st.plotly_chart(fig, key=None)
    else:
        st.info("시나리오를 구성하면 Monte Carlo 시뮬레이션 결과를 볼 수 있습니다.")
