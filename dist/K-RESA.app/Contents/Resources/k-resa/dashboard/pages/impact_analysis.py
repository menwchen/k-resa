"""Tab 3: 파급효과 분석"""

import streamlit as st
from dashboard.components.charts import (
    sankey_diagram, heatmap_chart, bar_chart, distribution_chart,
)
from dashboard.components.widgets import impact_summary_box
from models.impact_calculator import ImpactCalculator
from models.probability_model import ProbabilityModel
from utils.constants import SECTOR_NAMES_KR


def render(data_manager):
    """파급효과 분석 렌더링"""
    st.header("📈 파급효과 분석")

    scenario = st.session_state.get("current_scenario")
    if not scenario:
        st.warning("⚠️ 먼저 '시나리오 구성기' 탭에서 시나리오를 설정하세요.")
        return

    st.caption(f"분석 대상: **{scenario.name}**")

    # ─── 파급효과 계산 ───
    baseline = data_manager.get_all_baseline()
    calculator = ImpactCalculator(baseline)
    result = calculator.calculate(scenario)
    result_dict = calculator.result_to_dict(result)

    # 세션에 저장
    st.session_state["impact_result"] = result
    st.session_state["impact_result_dict"] = result_dict

    # ─── 요약 지표 ───
    impact_summary_box(result_dict)

    st.divider()

    # ─── 추가 지표 ───
    col1, col2, col3 = st.columns(3)
    with col1:
        ppi = result_dict.get("ppi_impact_pct", 0)
        st.metric("PPI 영향", f"{ppi:+.2f}%p")
    with col2:
        unemp = result_dict.get("unemployment_impact_pct", 0)
        st.metric("실업률 변동", f"{unemp:+.2f}%p")
    with col3:
        fx = result_dict.get("exchange_rate_impact_pct", 0)
        st.metric("환율 변동", f"{fx:+.1f}%")

    st.divider()

    # ─── 충격 전파 경로 (Sankey) ───
    st.subheader("🔀 충격 전파 경로")
    paths = result_dict.get("transmission_paths", [])
    if paths:
        fig = sankey_diagram(paths)
        st.plotly_chart(fig, use_container_width=True)

        with st.expander("전파 경로 상세"):
            for i, p in enumerate(paths, 1):
                st.markdown(f"**{i}.** {p.get('mechanism', '')}")
    else:
        st.info("전파 경로 데이터가 없습니다.")

    st.divider()

    # ─── 산업별 영향도 ───
    st.subheader("🏭 산업별 영향도")
    sector_impacts = result_dict.get("sector_impacts", {})

    if sector_impacts:
        # 히트맵
        fig = heatmap_chart(sector_impacts)
        st.plotly_chart(fig, use_container_width=True)

        # 총 영향 막대차트
        names = [v["name_kr"] for v in sector_impacts.values()]
        totals = [v["total_impact_pct"] for v in sector_impacts.values()]

        # 큰 순으로 정렬
        sorted_pairs = sorted(zip(names, totals), key=lambda x: x[1], reverse=True)
        names_sorted, totals_sorted = zip(*sorted_pairs)

        fig = bar_chart(
            list(names_sorted), list(totals_sorted),
            "산업별 총 영향도 (%)", orientation="h",
        )
        st.plotly_chart(fig, use_container_width=True)

        # 고용 위험 표시
        st.markdown("**고용 위험도:**")
        risk_cols = st.columns(len(sector_impacts))
        for col, (sector, info) in zip(risk_cols, sector_impacts.items()):
            risk = info.get("employment_risk", "low")
            emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(risk, "⚪")
            with col:
                st.markdown(f"{emoji} {info['name_kr']}")

    st.divider()

    # ─── 불확실성 분석 (Monte Carlo) ───
    st.subheader("📊 불확실성 분석")

    with st.spinner("Monte Carlo 시뮬레이션 실행 중..."):
        prob_model = ProbabilityModel(n_simulations=5000)
        dist = prob_model.impact_distribution(
            scenario, calculator, baseline, n_samples=2000
        )

    col1, col2 = st.columns(2)

    with col1:
        gdp_dist = dist["gdp"]
        fig = distribution_chart(
            gdp_dist["distribution"],
            f"GDP 영향 분포 (평균: {gdp_dist['mean']:.2f}%p)",
            xlabel="GDP 영향 (%p)",
            ci=(gdp_dist["p5"], gdp_dist["p95"]),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        cpi_dist = dist["cpi"]
        fig = distribution_chart(
            cpi_dist["distribution"],
            f"CPI 영향 분포 (평균: {cpi_dist['mean']:.2f}%p)",
            xlabel="CPI 영향 (%p)",
            ci=(cpi_dist["p5"], cpi_dist["p95"]),
        )
        st.plotly_chart(fig, use_container_width=True)

    # 요약 통계
    st.markdown(f"""
    | 지표 | 평균 | 표준편차 | 5% | 95% |
    |------|------|---------|-----|------|
    | GDP | {gdp_dist['mean']:+.2f}%p | {gdp_dist['std']:.2f} | {gdp_dist['p5']:+.2f} | {gdp_dist['p95']:+.2f} |
    | CPI | {cpi_dist['mean']:+.2f}%p | {cpi_dist['std']:.2f} | {cpi_dist['p5']:+.2f} | {cpi_dist['p95']:+.2f} |
    """)
