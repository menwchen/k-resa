"""K-RESA 상수 정의"""

# ─── FRED API 시리즈 코드 ───
FRED_SERIES = {
    "wti": "DCOILWTICO",
    "brent": "DCOILBRENTEU",
    "usd_krw": "DEXKOUS",
    "fed_rate": "FEDFUNDS",
    "wheat": "PWHEAMTUSDM",
    "corn": "PMAIZMTUSDM",
    "soybean": "PSOYBUSDM",
    "cpi_us": "CPIAUCSL",
    "vix": "VIXCLS",
}

# ─── 한국은행 ECOS 통계표 코드 ───
BOK_STAT_CODES = {
    "cpi": "901Y009",              # 4.2.1. 소비자물가지수 (M)
    "ppi": "404Y014",              # 4.1.1.1. 생산자물가지수(기본분류) (M)
    "import_price": "401Y015",     # 4.3.2.1. 수입물가지수(기본분류) (M)
    "gdp_real_sa": "200Y104",      # 경제활동별 GDP(계절조정,실질,분기) (Q)
    "gdp_nominal_sa": "200Y103",   # 경제활동별 GDP(계절조정,명목,분기) (Q)
    "trade_summary": "901Y118",    # 3.2.1. 수출입 총괄 (M)
    "current_account": "301Y017",  # 2.5.1.2. 경상수지(계절조정) (M)
    "base_rate": "722Y001",        # 1.3.1. 기준금리 및 여수신금리 (D)
    "exchange_rate_d": "731Y001",  # 3.1.1.1. 대원화환율 (D)
    "exchange_rate_m": "731Y004",  # 3.1.2.1. 대원화환율 (M)
    "employment": "901Y083",       # 8.6.8. 고용보험 가입자수 (M)
}

# ─── CPI 가중치 (2025 기준, 천분비) ───
CPI_WEIGHTS = {
    "energy": {
        "electricity": 27.4,
        "gas": 14.2,
        "gasoline": 32.1,
        "diesel": 8.5,
        "total": 82.2,
    },
    "food": {
        "grains": 18.5,
        "meat": 28.3,
        "dairy": 12.1,
        "vegetables": 21.8,
        "fruits": 14.2,
        "processed_food": 52.8,
        "total": 147.7,
    },
    "housing": 168.5,
    "transport": 112.3,
    "communication": 52.1,
    "education": 68.4,
    "others": 368.8,
}

# ─── 에너지 전가율 (pass-through rate) ───
ENERGY_PASSTHROUGH = {
    "oil_to_ppi": 0.35,          # 유가 → 생산자물가
    "oil_to_cpi": 0.15,          # 유가 → 소비자물가 (직접)
    "oil_to_cpi_indirect": 0.08, # 유가 → 소비자물가 (간접, PPI 경유)
    "lng_to_electricity": 0.42,  # LNG가격 → 전력요금
    "exchange_to_import": 0.65,  # 환율 → 수입물가
    "import_to_ppi": 0.30,       # 수입물가 → 생산자물가
    "ppi_to_cpi": 0.45,          # 생산자물가 → 소비자물가
}

# ─── 농산물 전가율 ───
AGRI_PASSTHROUGH = {
    "grain_to_feed": 0.72,       # 곡물가 → 사료가
    "feed_to_meat": 0.55,        # 사료가 → 육류가
    "fertilizer_to_crop": 0.38,  # 비료가 → 농산물가
    "grain_to_processed": 0.28,  # 곡물가 → 가공식품
    "food_to_cpi": 0.65,         # 식품 도매가 → CPI 식품
}

# ─── 환율 전가율 (exchange rate pass-through) ───
FX_PASSTHROUGH = {
    "to_import_price": 0.65,     # 환율 → 수입물가 (6개월)
    "to_ppi": 0.20,              # 환율 → 생산자물가
    "to_cpi": 0.08,              # 환율 → 소비자물가
    "lag_months": 3,             # 전가 시차 (월)
}

# ─── 정책 효과 계수 ───
POLICY_EFFECTS = {
    "rate_hike_25bp": {
        "gdp_impact_pct": -0.12,
        "cpi_impact_pct": -0.08,
        "exchange_rate_pct": -1.5,  # 원화 강세
        "lag_quarters": 4,
    },
    "oil_reserve_release_10mb": {
        "oil_price_impact_pct": -2.0,
        "duration_months": 3,
    },
    "energy_subsidy_1t_krw": {
        "cpi_impact_pct": -0.12,
        "fiscal_cost_t_krw": 1.0,
    },
    "food_tariff_cut_5ppt": {
        "food_cpi_impact_pct": -0.8,
        "tariff_revenue_loss_t_krw": 0.5,
    },
    "fiscal_spending_1t_krw": {
        "gdp_multiplier": 0.7,
        "lag_quarters": 2,
    },
}

# ─── 충격 수준 정의 ───
SHOCK_LEVELS = {
    "mild": {"label": "경미", "multiplier": 1.0},
    "moderate": {"label": "중간", "multiplier": 2.0},
    "severe": {"label": "심각", "multiplier": 3.5},
}

# ─── 시나리오 기본 확률 (사전 확률) ───
SCENARIO_PRIORS = {
    "energy_crisis": {"mild": 0.25, "moderate": 0.10, "severe": 0.03},
    "agri_crisis": {"mild": 0.20, "moderate": 0.08, "severe": 0.02},
    "financial_stress": {"mild": 0.20, "moderate": 0.08, "severe": 0.02},
}

# ─── 복합 위기 상호작용 계수 ───
COMPOUND_INTERACTION = {
    ("energy_crisis", "agri_crisis"): 1.15,        # 에너지+농산물: 비료/운송 비용 상승
    ("energy_crisis", "financial_stress"): 1.25,    # 에너지+금융: 기업 부채 부담 가중
    ("agri_crisis", "financial_stress"): 1.10,      # 농산물+금융: 식품업체 유동성 위기
    ("energy_crisis", "agri_crisis", "financial_stress"): 1.45,  # 3중 복합
}

# ─── 산업 분류 한글 매핑 ───
SECTOR_NAMES_KR = {
    "petrochemical": "석유화학",
    "steel": "철강",
    "auto": "자동차",
    "semiconductor": "반도체",
    "shipbuilding": "조선",
    "cement": "시멘트",
    "refining": "정유",
    "agriculture_livestock": "농축산",
    "services": "서비스",
}

# ─── 시각화 색상 ───
COLORS = {
    "energy": "#FF6B35",
    "agriculture": "#4CAF50",
    "finance": "#2196F3",
    "compound": "#9C27B0",
    "policy": "#FF9800",
    "positive": "#4CAF50",
    "negative": "#F44336",
    "neutral": "#9E9E9E",
    "bg_dark": "#0E1117",
    "bg_card": "#1E2130",
    "text": "#FAFAFA",
}
