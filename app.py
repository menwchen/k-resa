"""
K-RESA: 한국 경제 복합위기 시나리오 분석기
Korean Economy Risk & Event Scenario Analyzer
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st

st.set_page_config(
    page_title="K-RESA | 한국 경제 복합위기 시나리오 분석기",
    page_icon="🇰🇷",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── 스타일 ───
st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 20px;
        border-radius: 8px 8px 0 0;
    }
    div[data-testid="stMetricValue"] { font-size: 1.4rem; }
    .block-container { padding-top: 2rem; }
</style>
""", unsafe_allow_html=True)

# ─── 헤더 ───
st.markdown("# 🇰🇷 K-RESA")
st.markdown("**Korean Economy Risk & Event Scenario Analyzer** | 한국 경제 복합위기 시나리오 분석기")
st.markdown("---")

# ─── 데이터 매니저 초기화 ───
from data.data_manager import DataManager


@st.cache_resource
def get_data_manager():
    return DataManager()


dm = get_data_manager()

# ─── 탭 구성 ───
from dashboard.pages import overview, scenario_builder, impact_analysis, probability, policy_eval

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 현황 대시보드",
    "🎛️ 시나리오 구성",
    "📈 파급효과 분석",
    "🎲 확률 분석",
    "🏛️ 정책 대응",
])

with tab1:
    overview.render(dm)

with tab2:
    scenario_builder.render(dm)

with tab3:
    impact_analysis.render(dm)

with tab4:
    probability.render(dm)

with tab5:
    policy_eval.render(dm)

# ─── 사이드바 정보 ───
with st.sidebar:
    st.markdown("### ℹ️ K-RESA 정보")
    st.markdown("""
    **버전**: 1.0.0
    **데이터 소스**:
    - FRED API
    - 한국은행 ECOS API
    - EIA API
    - 수동 데이터 (YAML)

    **분석 기능**:
    1. 실시간 지표 모니터링
    2. 시나리오 구성 (프리셋/커스텀)
    3. 파급효과 산출
    4. 확률 분석 (베이지안/MC)
    5. 정책 대응 시뮬레이션
    """)

    st.markdown("---")

    if st.button("🔄 데이터 리로드"):
        st.cache_resource.clear()
        st.rerun()

    st.markdown("---")
    st.caption("© 2026 K-RESA Project")
