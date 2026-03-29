"""Tab 2: 시나리오 구성기"""

import streamlit as st
from dashboard.components.widgets import severity_selector, custom_shock_sliders
from models.scenario_engine import ScenarioEngine, Scenario


def render(data_manager):
    """시나리오 구성기 렌더링"""
    st.header("🎛️ 시나리오 구성기")
    st.caption("위기 유형과 충격 수준을 설정하여 분석 시나리오를 구성합니다")

    engine = ScenarioEngine()

    # ─── 모드 선택 ───
    mode = st.radio(
        "시나리오 구성 방식",
        ["프리셋 시나리오", "사용자 정의"],
        horizontal=True,
        key="scenario_mode",
    )

    if mode == "프리셋 시나리오":
        scenario = _preset_mode(engine)
    else:
        scenario = _custom_mode(engine)

    # 세션에 시나리오 저장
    if scenario:
        st.session_state["current_scenario"] = scenario
        _display_scenario_summary(scenario, engine)


def _preset_mode(engine: ScenarioEngine) -> Scenario | None:
    """프리셋 시나리오 모드"""
    severities = severity_selector(key_prefix="preset_")

    active = {k: v for k, v in severities.items() if v != "none"}

    if not active:
        st.info("👆 위에서 하나 이상의 위기 유형을 선택하세요")
        return None

    # 개별 시나리오 생성
    scenarios = []
    for crisis_type, severity in active.items():
        scenarios.append(engine.create_preset(crisis_type, severity))

    # 단일 vs 복합
    if len(scenarios) == 1:
        return scenarios[0]
    else:
        return engine.create_compound(scenarios)


def _custom_mode(engine: ScenarioEngine) -> Scenario | None:
    """사용자 정의 모드"""
    name = st.text_input("시나리오 이름", value="사용자 정의 시나리오",
                          key="custom_name")

    shock_params = custom_shock_sliders(key_prefix="custom_")

    # 하나라도 0이 아닌 값이 있으면 시나리오 생성
    if any(v != 0 for v in shock_params.values()):
        return engine.create_custom(name, shock_params)

    st.info("👆 슬라이더를 조정하여 충격 변수를 설정하세요")
    return None


def _display_scenario_summary(scenario: Scenario, engine: ScenarioEngine):
    """시나리오 요약 표시"""
    st.divider()
    st.subheader("📋 구성된 시나리오")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown(f"**{scenario.name}**")
        st.markdown(f"*{scenario.description}*")

        # 충격 변수 테이블
        shock_data = engine.scenario_to_dict(scenario)["shocks"]
        if shock_data:
            label_map = {
                "oil_price_change_pct": "유가 변동",
                "lng_price_change_pct": "LNG 가격 변동",
                "electricity_cost_change_pct": "전력비용 변동",
                "grain_price_change_pct": "곡물가 변동",
                "fertilizer_price_change_pct": "비료가 변동",
                "feed_price_change_pct": "사료가 변동",
                "credit_spread_change_bp": "신용스프레드 변동",
                "exchange_rate_change_pct": "환율 변동",
                "interest_rate_change_pct": "금리 변동",
            }
            unit_map = {
                "credit_spread_change_bp": "bp",
                "interest_rate_change_pct": "%p",
            }

            rows = []
            for k, v in shock_data.items():
                unit = unit_map.get(k, "%")
                rows.append({
                    "변수": label_map.get(k, k),
                    "변동": f"{v:+.1f}{unit}",
                })

            st.table(rows)

    with col2:
        st.metric("발생 확률", f"{scenario.probability * 100:.1f}%")
        st.metric("위기 유형", scenario.crisis_type.replace("_", " ").title())

        if scenario.sub_scenarios:
            st.markdown("**구성 요소:**")
            for sub in scenario.sub_scenarios:
                st.markdown(f"- {sub.name}")

    st.success("✅ 시나리오가 구성되었습니다. '파급효과 분석' 탭에서 결과를 확인하세요.")
