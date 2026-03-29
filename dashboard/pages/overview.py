"""Tab 1: 현황 대시보드"""

import streamlit as st
import pandas as pd
from dashboard.components.charts import line_chart, pie_chart, bar_chart
from dashboard.components.widgets import metric_row
from utils.helpers import format_pct, format_usd


def render(data_manager):
    """현황 대시보드 렌더링"""
    st.header("📊 현황 대시보드")
    st.caption("주요 경제 지표 현황 및 추이")

    # ─── 주요 지표 카드 ───
    indicators = data_manager.get_current_indicators()
    st.session_state["_cached_indicators"] = indicators

    def _safe(val, default=0):
        return default if val is None else val

    row1 = [
        {"label": "WTI 유가", "value": format_usd(_safe(indicators.get("oil_wti"), 0)),
         "delta": None},
        {"label": "Brent 유가", "value": format_usd(_safe(indicators.get("oil_brent"), 0)),
         "delta": None},
        {"label": "USD/KRW 환율", "value": f"{_safe(indicators.get('usd_krw'), 0):,.0f}원",
         "delta": None},
        {"label": "기준금리", "value": f"{_safe(indicators.get('base_rate'), 0):.2f}%",
         "delta": None},
    ]
    metric_row(row1)

    st.divider()

    row2 = [
        {"label": "소비자물가(CPI)", "value": format_pct(_safe(indicators.get("cpi_yoy"), 0)),
         "delta": None},
        {"label": "GDP 성장률", "value": format_pct(_safe(indicators.get("gdp_growth"), 0)),
         "delta": None},
        {"label": "실업률", "value": f"{_safe(indicators.get('unemployment'), 0):.1f}%",
         "delta": None},
        {"label": "무역수지", "value": f"{_safe(indicators.get('trade_balance'), 0):+.1f}B$",
         "delta": None},
    ]
    metric_row(row2)

    st.divider()

    # ─── 구조 데이터 시각화 ───
    col1, col2 = st.columns(2)

    with col1:
        # 원유 수입 국가별 비중
        oil_data = data_manager.get_energy_data()
        oil_import = oil_data.get("korea_oil_import", {}).get("by_country_pct", {})
        if oil_import:
            name_map = {
                "middle_east": "중동(기타)", "saudi_arabia": "사우디",
                "uae": "UAE", "iraq": "이라크", "kuwait": "쿠웨이트",
                "us": "미국", "russia": "러시아", "others": "기타",
            }
            labels = [name_map.get(k, k) for k in oil_import.keys()]
            values = list(oil_import.values())
            fig = pie_chart(labels, values, "원유 수입 국가별 비중 (%)")
            st.plotly_chart(fig, key=None)

    with col2:
        # 전력 생산 구성
        power_mix = oil_data.get("power_generation_mix_pct", {})
        power_mix_clean = {k: v for k, v in power_mix.items() if k != "source"}
        if power_mix_clean:
            name_map = {
                "coal": "석탄", "lng": "LNG", "nuclear": "원자력",
                "renewables": "신재생", "oil": "석유", "others": "기타",
            }
            labels = [name_map.get(k, k) for k in power_mix_clean.keys()]
            values = list(power_mix_clean.values())
            fig = pie_chart(labels, values, "전력 생산 구성 (%)")
            st.plotly_chart(fig, key=None)

    # ─── 산업별 GDP 비중 ───
    sectors = data_manager.get_sector_data()
    if sectors:
        from utils.constants import SECTOR_NAMES_KR
        names = [SECTOR_NAMES_KR.get(s, s) for s in sectors.keys()]
        gdp_shares = [info.get("gdp_share_pct", 0) for info in sectors.values()]

        fig = bar_chart(names, gdp_shares, "산업별 GDP 비중 (%)", color="#4FC3F7")
        st.plotly_chart(fig, key=None)

    # ─── 데이터 수집 상태 ───
    with st.expander("📡 데이터 수집 상태"):
        from utils.helpers import get_api_key
        sources = [
            ("FRED API", "fred", "유가, 곡물, 미국 금리"),
            ("한국은행 ECOS", "bok_ecos", "CPI, PPI, 기준금리, 환율, GDP"),
            ("KOSIS (국가통계포털)", "kosis", "실업률, 고용, 인구"),
            ("EIA API", "eia", "에너지 생산/수입 데이터"),
        ]
        rows = []
        for name, key_name, desc in sources:
            has_key = bool(get_api_key(key_name))
            status = "✅ 연결됨" if has_key else "⚠️ API 키 필요"
            note = desc if has_key else f"`config/settings.yaml` → `{key_name}` 설정 필요"
            rows.append(f"| {name} | {status} | {note} |")

        rows.append("| 수동 데이터 | ✅ 로드 완료 | `config/manual_data.yaml` |")

        table = "| 소스 | 상태 | 비고 |\n|------|------|------|\n" + "\n".join(rows)
        st.markdown(table)

        missing = [name for name, key_name, _ in sources if not get_api_key(key_name)]
        if missing:
            st.info("API 키가 없는 소스는 수동 데이터(manual_data.yaml)의 기본값을 사용합니다.")
