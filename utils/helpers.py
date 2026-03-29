"""K-RESA 유틸리티 함수"""

import os
import yaml
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path


def get_project_root() -> Path:
    """프로젝트 루트 디렉토리 반환"""
    return Path(__file__).parent.parent


def load_yaml(filepath: str) -> dict:
    """YAML 파일 로드"""
    path = get_project_root() / filepath
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_yaml(data: dict, filepath: str):
    """YAML 파일 저장"""
    path = get_project_root() / filepath
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False)


def get_cache_path(key: str, cache_dir: str = "data/cache") -> Path:
    """캐시 파일 경로 생성"""
    hashed = hashlib.md5(key.encode()).hexdigest()[:12]
    cache_path = get_project_root() / cache_dir
    cache_path.mkdir(parents=True, exist_ok=True)
    return cache_path / f"{hashed}.json"


def load_cache(key: str, ttl_hours: int = 24) -> dict | None:
    """캐시 로드 (TTL 체크)"""
    path = get_cache_path(key)
    if not path.exists():
        return None
    try:
        with open(path, "r") as f:
            cached = json.load(f)
        cached_time = datetime.fromisoformat(cached.get("_cached_at", "2000-01-01"))
        if datetime.now() - cached_time > timedelta(hours=ttl_hours):
            return None
        return cached.get("data")
    except (json.JSONDecodeError, KeyError):
        return None


def save_cache(key: str, data):
    """캐시 저장"""
    path = get_cache_path(key)
    with open(path, "w") as f:
        json.dump({"_cached_at": datetime.now().isoformat(), "data": data}, f, default=str)


def pct_change(new_val: float, old_val: float) -> float:
    """변화율 계산 (%)"""
    if old_val == 0:
        return 0.0
    return ((new_val - old_val) / old_val) * 100


def format_krw(value_trillion: float) -> str:
    """조원 단위 포맷팅"""
    if abs(value_trillion) >= 1:
        return f"{value_trillion:,.1f}조원"
    return f"{value_trillion * 10000:,.0f}억원"


def format_pct(value: float, decimals: int = 1) -> str:
    """퍼센트 포맷팅 (부호 포함)"""
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.{decimals}f}%"


def format_usd(value: float) -> str:
    """USD 포맷팅"""
    return f"${value:,.2f}"


def clamp(value: float, min_val: float, max_val: float) -> float:
    """값 범위 제한"""
    return max(min_val, min(max_val, value))


def get_api_key(service: str) -> str:
    """API 키 조회 (우선순위: st.secrets > 환경변수 > settings.yaml)"""
    # 1. Streamlit Cloud secrets (배포 환경)
    try:
        import streamlit as st
        return st.secrets["api_keys"][service]
    except Exception:
        pass

    # 2. 환경변수
    env_key = f"KRESA_{service.upper()}_API_KEY"
    key = os.environ.get(env_key, "")
    if key:
        return key

    # 3. 로컬 설정 파일
    try:
        settings = load_yaml("config/settings.yaml")
        return settings.get("api_keys", {}).get(service, "")
    except FileNotFoundError:
        return ""
