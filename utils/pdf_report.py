"""K-RESA 1페이지 PDF 보고서 생성"""

import io
from datetime import datetime
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.patches as mpatches
import numpy as np


# 한글 폰트 설정 (macOS)
for font in ["AppleGothic", "Apple SD Gothic Neo", "Malgun Gothic", "NanumGothic"]:
    try:
        plt.rcParams["font.family"] = font
        plt.rcParams["axes.unicode_minus"] = False
        break
    except Exception:
        continue


def generate_report(scenario, impact_dict, policy_pkg, indicators) -> bytes:
    """1페이지 PDF 보고서 생성 → bytes 반환"""

    fig = plt.figure(figsize=(11.69, 8.27), dpi=150)  # A4 가로
    fig.patch.set_facecolor("#0E1117")

    # ─── 전체 레이아웃 (6행 × 4열 그리드) ───
    gs = fig.add_gridspec(6, 4, hspace=0.6, wspace=0.4,
                          left=0.06, right=0.94, top=0.92, bottom=0.04)

    white = "#FAFAFA"
    orange = "#FF6B35"
    green = "#4CAF50"
    red = "#F44336"
    blue = "#2196F3"
    gray = "#888888"
    bg = "#1E2130"

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # ════════════════════════════════════════
    # 헤더
    # ════════════════════════════════════════
    fig.text(0.06, 0.97, "K-RESA 복합위기 시나리오 분석 보고서",
             fontsize=16, fontweight="bold", color=white)
    fig.text(0.06, 0.94, f"시나리오: {scenario.name}  |  작성: {now}  |  개발: 송종운",
             fontsize=8, color=gray)
    fig.text(0.94, 0.97, "CONFIDENTIAL", fontsize=7, color=orange, ha="right",
             fontstyle="italic")

    # 구분선
    fig.add_artist(plt.Line2D([0.06, 0.94], [0.935, 0.935],
                              color=orange, linewidth=1.5))

    # ════════════════════════════════════════
    # Row 1: 현황 지표 카드 (4개)
    # ════════════════════════════════════════
    cards = [
        ("유가 (WTI)", f"${indicators.get('oil_wti', 0):,.1f}", orange),
        ("환율 (USD/KRW)", f"{indicators.get('usd_krw', 0):,.0f}원", blue),
        ("기준금리", f"{indicators.get('base_rate', 0):.2f}%", green),
        ("CPI 상승률", f"{indicators.get('cpi_yoy', 0):+.1f}%", red),
    ]
    for i, (label, value, color) in enumerate(cards):
        ax = fig.add_subplot(gs[0, i])
        ax.set_facecolor(bg)
        ax.set_xlim(0, 1); ax.set_ylim(0, 1)
        ax.axis("off")
        ax.text(0.5, 0.7, value, fontsize=14, fontweight="bold",
                color=color, ha="center", va="center")
        ax.text(0.5, 0.25, label, fontsize=7, color=gray, ha="center")
        for spine in ax.spines.values():
            spine.set_visible(False)

    # ════════════════════════════════════════
    # Row 2: 충격 영향 요약 (Before)
    # ════════════════════════════════════════
    ax = fig.add_subplot(gs[1, :2])
    ax.set_facecolor(bg)
    ax.axis("off")
    ax.set_title("충격 영향 (정책 미적용)", fontsize=9, fontweight="bold",
                 color=white, loc="left", pad=8)

    gdp_i = impact_dict.get("gdp_impact_pct", 0)
    cpi_i = impact_dict.get("cpi_impact_pct", 0)
    tb_i = impact_dict.get("trade_balance_impact_billion_usd", 0)
    unemp_i = impact_dict.get("unemployment_impact_pct", 0)

    impact_items = [
        f"GDP: {gdp_i:+.2f}%p",
        f"CPI: {cpi_i:+.2f}%p",
        f"무역수지: {tb_i:+.1f}B$",
        f"실업률: {unemp_i:+.2f}%p",
    ]
    for j, text in enumerate(impact_items):
        color = red if "-" in text.split(":")[1] or ("+0" not in text.split(":")[1] and "CPI" in text) else green
        if "CPI" in text and "+" in text.split(":")[1]:
            color = red
        ax.text(0.05 + (j % 2) * 0.5, 0.55 - (j // 2) * 0.45, text,
                fontsize=10, color=color, fontweight="bold")

    # ════════════════════════════════════════
    # Row 2 right: 정책 효과 요약 (After)
    # ════════════════════════════════════════
    ax = fig.add_subplot(gs[1, 2:])
    ax.set_facecolor(bg)
    ax.axis("off")

    if policy_pkg:
        ax.set_title(f"정책 대응: {policy_pkg.name}", fontsize=9, fontweight="bold",
                     color=white, loc="left", pad=8)
        policy_items = [
            f"순 GDP: {policy_pkg.net_gdp_after_shock_pct:+.2f}%p",
            f"순 CPI: {policy_pkg.net_cpi_after_shock_pct:+.2f}%p",
            f"재정비용: {policy_pkg.total_fiscal_cost_trillion_krw:.1f}조원",
            f"효과성: {policy_pkg.effectiveness_score:.1f}점",
        ]
        for j, text in enumerate(policy_items):
            ax.text(0.05 + (j % 2) * 0.5, 0.55 - (j // 2) * 0.45, text,
                    fontsize=10, color=blue, fontweight="bold")
    else:
        ax.text(0.5, 0.5, "정책 미선택", fontsize=10, color=gray, ha="center")

    # ════════════════════════════════════════
    # Row 3-4: 산업별 영향도 수평 막대 차트
    # ════════════════════════════════════════
    ax = fig.add_subplot(gs[2:4, :2])
    ax.set_facecolor(bg)

    sector_impacts = impact_dict.get("sector_impacts", {})
    if sector_impacts:
        names = [v["name_kr"] for v in sector_impacts.values()]
        totals = [v["total_impact_pct"] for v in sector_impacts.values()]

        # 정렬
        pairs = sorted(zip(names, totals), key=lambda x: x[1])
        names_s, totals_s = zip(*pairs)

        colors_bar = [red if v > 3 else orange if v > 1 else green for v in totals_s]
        y_pos = range(len(names_s))
        ax.barh(y_pos, totals_s, color=colors_bar, height=0.6, alpha=0.85)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(names_s, fontsize=7, color=white)
        ax.set_xlabel("영향도 (%)", fontsize=7, color=gray)
        ax.tick_params(axis="x", colors=gray, labelsize=6)
        ax.set_title("산업별 충격 영향도", fontsize=9, fontweight="bold",
                     color=white, loc="left", pad=8)
        for val, y in zip(totals_s, y_pos):
            ax.text(val + 0.1, y, f"{val:.1f}%", fontsize=6, color=white, va="center")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_color(gray)
    ax.spines["left"].set_color(gray)

    # ════════════════════════════════════════
    # Row 3-4: 충격 전파 경로 텍스트
    # ════════════════════════════════════════
    ax = fig.add_subplot(gs[2:4, 2:])
    ax.set_facecolor(bg)
    ax.axis("off")
    ax.set_title("충격 전파 경로", fontsize=9, fontweight="bold",
                 color=white, loc="left", pad=8)

    paths = impact_dict.get("transmission_paths", [])
    for j, p in enumerate(paths[:8]):
        mechanism = p.get("mechanism", "")
        if len(mechanism) > 45:
            mechanism = mechanism[:45] + "..."
        ax.text(0.05, 0.88 - j * 0.115, f"→ {mechanism}",
                fontsize=6.5, color=white, fontfamily="monospace")

    # ════════════════════════════════════════
    # Row 5-6: 정책 도구별 효과 (테이블)
    # ════════════════════════════════════════
    ax = fig.add_subplot(gs[4:, :])
    ax.set_facecolor(bg)
    ax.axis("off")
    ax.set_title("정책 도구별 효과 상세", fontsize=9, fontweight="bold",
                 color=white, loc="left", pad=8)

    if policy_pkg and policy_pkg.actions:
        headers = ["정책 도구", "규모", "GDP 효과", "CPI 효과", "재정비용", "시차"]
        col_x = [0.02, 0.22, 0.38, 0.52, 0.66, 0.80]

        for k, h in enumerate(headers):
            ax.text(col_x[k], 0.85, h, fontsize=7, fontweight="bold",
                    color=orange)

        ax.add_artist(plt.Line2D([0.02, 0.92], [0.82, 0.82],
                                  color=gray, linewidth=0.5))

        for j, a in enumerate(policy_pkg.actions[:7]):
            y = 0.73 - j * 0.10
            row = [
                a.name,
                f"{a.magnitude}{a.unit}",
                f"{a.gdp_effect_pct:+.3f}%p",
                f"{a.cpi_effect_pct:+.3f}%p",
                f"{a.fiscal_cost_trillion_krw:.1f}조원",
                f"{a.lag_quarters}분기",
            ]
            for k, val in enumerate(row):
                c = white
                if k == 2:
                    c = green if a.gdp_effect_pct > 0 else red
                elif k == 3:
                    c = green if a.cpi_effect_pct < 0 else red
                ax.text(col_x[k], y, val, fontsize=6.5, color=c)

        # 합계선
        total_y = 0.73 - len(policy_pkg.actions) * 0.10 - 0.02
        ax.add_artist(plt.Line2D([0.02, 0.92], [total_y + 0.04, total_y + 0.04],
                                  color=gray, linewidth=0.5))
        ax.text(col_x[0], total_y, "합계", fontsize=7, fontweight="bold", color=orange)
        ax.text(col_x[2], total_y, f"{policy_pkg.total_gdp_effect_pct:+.3f}%p",
                fontsize=7, fontweight="bold", color=green if policy_pkg.total_gdp_effect_pct > 0 else red)
        ax.text(col_x[3], total_y, f"{policy_pkg.total_cpi_effect_pct:+.3f}%p",
                fontsize=7, fontweight="bold", color=green if policy_pkg.total_cpi_effect_pct < 0 else red)
        ax.text(col_x[4], total_y, f"{policy_pkg.total_fiscal_cost_trillion_krw:.1f}조원",
                fontsize=7, fontweight="bold", color=white)
    else:
        ax.text(0.5, 0.5, "정책을 선택하면 상세 분석이 표시됩니다",
                fontsize=9, color=gray, ha="center")

    # ─── 푸터 ───
    fig.text(0.06, 0.01, "K-RESA (Risk & Event Scenario Analyzer) | © 2026 송종운 (menwchen@mac.com)",
             fontsize=6, color=gray)
    fig.text(0.94, 0.01, f"생성: {now}", fontsize=6, color=gray, ha="right")

    # ─── PDF 출력 ───
    buf = io.BytesIO()
    fig.savefig(buf, format="pdf", facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()
