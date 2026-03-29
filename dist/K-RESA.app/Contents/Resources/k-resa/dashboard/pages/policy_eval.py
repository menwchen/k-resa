"""Tab 5: 정책 대응 평가"""

import streamlit as st
import pandas as pd
from dashboard.components.charts import radar_chart, bar_chart
from dashboard.components.widgets import policy_selector
from models.policy_simulator import PolicySimulator
from models.impact_calculator import ImpactResult


def render(data_manager):
    """정책 대응 평가 렌더링"""
    st.header("🏛️ 정책 대응 평가")

    impact_result = st.session_state.get("impact_result")
    if not impact_result:
        st.warning("⚠️ 먼저 '시나리오 구성기'에서 시나리오를 설정하고, '파급효과 분석'을 실행하세요.")
        return

    scenario = st.session_state.get("current_scenario")
    st.caption(f"대상 시나리오: **{scenario.name if scenario else '미설정'}**")

    simulator = PolicySimulator()

    # ─── 충격 요약 (before) ───
    st.subheader("⚡ 현재 충격 영향 (정책 미적용)")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("GDP", f"{impact_result.gdp_impact_pct:+.2f}%p")
    with col2:
        st.metric("CPI", f"{impact_result.cpi_impact_pct:+.2f}%p")
    with col3:
        st.metric("무역수지", f"{impact_result.trade_balance_impact_billion_usd:+.1f}B$")
    with col4:
        st.metric("실업률", f"{impact_result.unemployment_impact_pct:+.2f}%p")

    st.divider()

    # ─── 정책 선택 모드 ───
    mode = st.radio(
        "정책 구성 방식",
        ["프리셋 패키지 비교", "사용자 정의 패키지"],
        horizontal=True,
        key="policy_mode",
    )

    if mode == "프리셋 패키지 비교":
        _preset_comparison(simulator, impact_result)
    else:
        _custom_policy(simulator, impact_result)


def _preset_comparison(simulator: PolicySimulator, impact_result: ImpactResult):
    """프리셋 패키지 비교"""
    st.subheader("📦 정책 패키지 비교")

    packages = []
    for preset in simulator.preset_packages():
        pkg = simulator.build_preset_package(preset["name"])
        pkg = simulator.evaluate_against_shock(pkg, impact_result)
        packages.append((preset, pkg))

    # 비교 테이블
    rows = []
    for preset, pkg in packages:
        rows.append({
            "패키지": preset["name"],
            "설명": preset["description"],
            "GDP 효과": f"{pkg.total_gdp_effect_pct:+.2f}%p",
            "CPI 효과": f"{pkg.total_cpi_effect_pct:+.2f}%p",
            "순 GDP": f"{pkg.net_gdp_after_shock_pct:+.2f}%p",
            "순 CPI": f"{pkg.net_cpi_after_shock_pct:+.2f}%p",
            "재정비용": f"{pkg.total_fiscal_cost_trillion_krw:.1f}조원",
            "효과성": f"{pkg.effectiveness_score:.1f}",
        })

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # 레이더 차트 비교
    categories = ["GDP 개선", "CPI 억제", "비용 효율", "즉시성", "실업 완화"]

    values_list = []
    names = []
    for preset, pkg in packages:
        gdp_score = min(max(pkg.total_gdp_effect_pct * 10, 0), 10)
        cpi_score = min(max(-pkg.total_cpi_effect_pct * 5, 0), 10)
        cost_score = max(10 - pkg.total_fiscal_cost_trillion_krw / 5, 0)
        # 즉시성: 시차 없는 정책 비율
        immediate = sum(1 for a in pkg.actions if a.lag_quarters == 0)
        speed_score = (immediate / max(len(pkg.actions), 1)) * 10
        unemp_score = min(max(pkg.total_gdp_effect_pct * 4, 0), 10)

        values_list.append([gdp_score, cpi_score, cost_score, speed_score, unemp_score])
        names.append(preset["name"])

    fig = radar_chart(categories, values_list, names, "정책 패키지 종합 비교")
    st.plotly_chart(fig, use_container_width=True)

    # 세부 정책 내역
    for preset, pkg in packages:
        with st.expander(f"📋 {preset['name']} 세부 내역"):
            for a in pkg.actions:
                st.markdown(
                    f"- **{a.name}** ({a.magnitude}{a.unit}): "
                    f"GDP {a.gdp_effect_pct:+.3f}%p, CPI {a.cpi_effect_pct:+.3f}%p, "
                    f"비용 {a.fiscal_cost_trillion_krw:.1f}조원, "
                    f"시차 {a.lag_quarters}분기"
                )


def _custom_policy(simulator: PolicySimulator, impact_result: ImpactResult):
    """사용자 정의 정책"""
    st.subheader("🔧 사용자 정의 정책 패키지")

    tools_info = simulator.get_policy_tools_info()
    selected_actions = policy_selector(tools_info, key_prefix="custom_pol_")

    if not selected_actions:
        st.info("👆 정책 도구를 선택하고 강도를 조절하세요")
        return

    # 패키지 빌드
    actions = [simulator.create_action(tool, mag) for tool, mag in selected_actions]
    pkg = simulator.create_package("사용자 정의 패키지", actions)
    pkg = simulator.evaluate_against_shock(pkg, impact_result)

    st.divider()

    # 결과 표시
    st.subheader("📊 정책 적용 결과")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**충격 (Before)**")
        st.metric("GDP", f"{impact_result.gdp_impact_pct:+.2f}%p")
        st.metric("CPI", f"{impact_result.cpi_impact_pct:+.2f}%p")

    with col2:
        st.markdown("**정책 효과**")
        st.metric("GDP 효과", f"{pkg.total_gdp_effect_pct:+.2f}%p")
        st.metric("CPI 효과", f"{pkg.total_cpi_effect_pct:+.2f}%p")

    with col3:
        st.markdown("**순 영향 (After)**")
        st.metric("순 GDP", f"{pkg.net_gdp_after_shock_pct:+.2f}%p",
                   delta=f"{pkg.total_gdp_effect_pct:+.2f}%p")
        st.metric("순 CPI", f"{pkg.net_cpi_after_shock_pct:+.2f}%p",
                   delta=f"{pkg.total_cpi_effect_pct:+.2f}%p",
                   delta_color="inverse")

    st.divider()

    # 비용-효과 요약
    col1, col2 = st.columns(2)
    with col1:
        st.metric("총 재정비용", f"{pkg.total_fiscal_cost_trillion_krw:.1f}조원")
    with col2:
        st.metric("비용-효과 점수", f"{pkg.effectiveness_score:.1f}")

    # 정책별 효과 막대차트
    action_names = [a.name for a in pkg.actions]
    gdp_effects = [a.gdp_effect_pct for a in pkg.actions]
    cpi_effects = [a.cpi_effect_pct for a in pkg.actions]

    col1, col2 = st.columns(2)
    with col1:
        fig = bar_chart(action_names, gdp_effects, "정책별 GDP 효과 (%p)")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig = bar_chart(action_names, cpi_effects, "정책별 CPI 효과 (%p)")
        st.plotly_chart(fig, use_container_width=True)
