"""공통 위젯 컴포넌트"""

import streamlit as st
from utils.constants import COLORS


def metric_row(metrics: list[dict]):
    """지표 카드 행 표시"""
    cols = st.columns(len(metrics))
    for col, m in zip(cols, metrics):
        with col:
            delta = m.get("delta")
            delta_str = None
            if delta is not None:
                delta_str = f"{delta:+.1f}%"
            st.metric(
                label=m["label"],
                value=m["value"],
                delta=delta_str,
            )


def severity_selector(key_prefix: str = "") -> dict:
    """위기 유형별 심각도 선택"""
    severity_map = {"없음": "none", "경미": "mild", "중간": "moderate", "심각": "severe"}
    options = list(severity_map.keys())

    st.markdown("#### 위기 유형별 충격 수준")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**🛢️ 에너지 위기**")
        energy = st.select_slider(
            "에너지", options=options, value="없음",
            key=f"{key_prefix}energy_severity",
            label_visibility="collapsed",
        )

    with col2:
        st.markdown("**🌾 농산물 위기**")
        agri = st.select_slider(
            "농산물", options=options, value="없음",
            key=f"{key_prefix}agri_severity",
            label_visibility="collapsed",
        )

    with col3:
        st.markdown("**💰 금융 불안**")
        finance = st.select_slider(
            "금융", options=options, value="없음",
            key=f"{key_prefix}finance_severity",
            label_visibility="collapsed",
        )

    return {
        "energy_crisis": severity_map[energy],
        "agri_crisis": severity_map[agri],
        "financial_stress": severity_map[finance],
    }


def custom_shock_sliders(key_prefix: str = "") -> dict:
    """사용자 정의 충격 슬라이더"""
    st.markdown("#### 세부 충격 변수 조정")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**에너지**")
        oil = st.slider("유가 변동 (%)", -30, 200, 0, 5,
                         key=f"{key_prefix}oil")
        lng = st.slider("LNG 가격 변동 (%)", -20, 150, 0, 5,
                         key=f"{key_prefix}lng")
        elec = st.slider("전력비용 변동 (%)", -10, 80, 0, 5,
                          key=f"{key_prefix}elec")

        st.markdown("**농산물**")
        grain = st.slider("곡물가 변동 (%)", -20, 150, 0, 5,
                           key=f"{key_prefix}grain")
        fert = st.slider("비료가 변동 (%)", -20, 100, 0, 5,
                          key=f"{key_prefix}fert")

    with col2:
        st.markdown("**금융**")
        spread = st.slider("신용스프레드 변동 (bp)", -50, 500, 0, 10,
                            key=f"{key_prefix}spread")
        fx = st.slider("환율 변동 (%)", -15, 40, 0, 1,
                        key=f"{key_prefix}fx")
        rate = st.slider("금리 변동 (%p)", -1.0, 3.0, 0.0, 0.25,
                          key=f"{key_prefix}rate")

        st.markdown("**농산물 (계속)**")
        feed = st.slider("사료가 변동 (%)", -20, 120, 0, 5,
                          key=f"{key_prefix}feed")

    return {
        "oil_price_change_pct": oil,
        "lng_price_change_pct": lng,
        "electricity_cost_change_pct": elec,
        "grain_price_change_pct": grain,
        "fertilizer_price_change_pct": fert,
        "feed_price_change_pct": feed,
        "credit_spread_change_bp": spread,
        "exchange_rate_change_pct": fx,
        "interest_rate_change_pct": rate,
    }


def evidence_input(key_prefix: str = "") -> list[dict]:
    """베이지안 업데이트용 증거 입력"""
    st.markdown("#### 관측 증거 (확률 조정)")

    evidence = []
    evidence_options = [
        ("유가 상승 추세 지속", 1.4),
        ("호르무즈 해협 긴장 고조", 1.8),
        ("OPEC 감산 발표", 1.3),
        ("엘니뇨 발생", 1.5),
        ("우크라이나 곡물 수출 차질", 1.6),
        ("미 연준 금리 동결", 0.8),
        ("중국 경기 둔화", 1.3),
        ("글로벌 경기 회복 신호", 0.6),
        ("한국 수출 호조", 0.7),
        ("원자재 가격 안정화", 0.5),
    ]

    selected = st.multiselect(
        "관측된 이벤트를 선택하세요:",
        options=[e[0] for e in evidence_options],
        key=f"{key_prefix}evidence",
    )

    lr_map = {name: lr for name, lr in evidence_options}
    for name in selected:
        evidence.append({
            "name": name,
            "likelihood_ratio": lr_map[name],
        })

    return evidence


def policy_selector(policy_tools: list[dict],
                     key_prefix: str = "") -> list[tuple]:
    """정책 도구 선택기"""
    st.markdown("#### 정책 도구 선택")

    selected_actions = []

    for tool in policy_tools:
        col1, col2 = st.columns([3, 2])
        with col1:
            enabled = st.checkbox(
                f"{tool['name']}",
                key=f"{key_prefix}pol_{tool['key']}",
                help=tool["description"],
            )
        with col2:
            if enabled:
                magnitude = st.slider(
                    f"{tool['unit']}",
                    min_value=float(tool["range"][0]),
                    max_value=float(tool["range"][1]),
                    value=float(tool["range"][0]),
                    step=float(tool["step"]),
                    key=f"{key_prefix}pol_mag_{tool['key']}",
                    label_visibility="collapsed",
                )
                selected_actions.append((tool["key"], magnitude))

    return selected_actions


def impact_summary_box(result_dict: dict):
    """파급효과 요약 박스"""
    col1, col2, col3 = st.columns(3)

    with col1:
        gdp = result_dict.get("gdp_impact_pct", 0)
        st.metric("GDP 영향", f"{gdp:+.2f}%p",
                   delta=f"{gdp:+.2f}%p",
                   delta_color="inverse")

    with col2:
        cpi = result_dict.get("cpi_impact_pct", 0)
        st.metric("CPI 영향", f"{cpi:+.2f}%p",
                   delta=f"{cpi:+.2f}%p",
                   delta_color="inverse")

    with col3:
        tb = result_dict.get("trade_balance_impact_billion_usd", 0)
        st.metric("무역수지", f"{tb:+.1f}B$",
                   delta=f"{tb:+.1f}B$",
                   delta_color="inverse")
