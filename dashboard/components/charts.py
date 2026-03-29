"""공통 차트 컴포넌트"""

import plotly.graph_objects as go
import plotly.express as px
import numpy as np
from utils.constants import COLORS, SECTOR_NAMES_KR


def create_metric_card_data(label: str, value: float, unit: str,
                             delta: float = None) -> dict:
    """Streamlit metric 카드용 데이터"""
    return {"label": label, "value": f"{value:,.1f}{unit}", "delta": delta}


def line_chart(df, x_col: str, y_cols: list, title: str,
               colors: list = None) -> go.Figure:
    """시계열 라인 차트"""
    fig = go.Figure()
    default_colors = [COLORS["energy"], COLORS["agriculture"],
                      COLORS["finance"], COLORS["compound"]]

    for i, col in enumerate(y_cols):
        color = colors[i] if colors and i < len(colors) else default_colors[i % len(default_colors)]
        fig.add_trace(go.Scatter(
            x=df[x_col], y=df[col], name=col,
            line=dict(color=color, width=2),
            mode="lines",
        ))

    fig.update_layout(
        title=title,
        template="plotly_dark",
        paper_bgcolor=COLORS["bg_dark"],
        plot_bgcolor=COLORS["bg_dark"],
        height=400,
        margin=dict(l=40, r=20, t=50, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return fig


def bar_chart(categories: list, values: list, title: str,
              orientation: str = "v", color: str = None) -> go.Figure:
    """막대 차트"""
    bar_colors = [COLORS["negative"] if v < 0 else COLORS["positive"] for v in values]
    if color:
        bar_colors = [color] * len(values)

    if orientation == "h":
        fig = go.Figure(go.Bar(y=categories, x=values, orientation="h",
                               marker_color=bar_colors))
    else:
        fig = go.Figure(go.Bar(x=categories, y=values, marker_color=bar_colors))

    fig.update_layout(
        title=title,
        template="plotly_dark",
        paper_bgcolor=COLORS["bg_dark"],
        plot_bgcolor=COLORS["bg_dark"],
        height=400,
        margin=dict(l=40, r=20, t=50, b=40),
    )
    return fig


def heatmap_chart(sectors: dict, title: str = "산업별 영향도") -> go.Figure:
    """산업별 영향도 히트맵"""
    names = []
    energy_vals = []
    import_vals = []
    finance_vals = []

    for sector, info in sectors.items():
        names.append(info.get("name_kr", sector))
        energy_vals.append(info.get("energy_impact_pct", 0))
        import_vals.append(info.get("import_impact_pct", 0))
        finance_vals.append(info.get("finance_impact_pct", 0))

    z = [energy_vals, import_vals, finance_vals]
    y_labels = ["에너지 충격", "수입비용 충격", "금융 충격"]

    fig = go.Figure(go.Heatmap(
        z=z, x=names, y=y_labels,
        colorscale="RdYlGn_r",
        text=[[f"{v:.1f}%" for v in row] for row in z],
        texttemplate="%{text}",
        hovertemplate="산업: %{x}<br>충격: %{y}<br>영향: %{z:.2f}%<extra></extra>",
    ))

    fig.update_layout(
        title=title,
        template="plotly_dark",
        paper_bgcolor=COLORS["bg_dark"],
        plot_bgcolor=COLORS["bg_dark"],
        height=350,
        margin=dict(l=100, r=20, t=50, b=60),
    )
    return fig


def sankey_diagram(paths: list, title: str = "충격 전파 경로") -> go.Figure:
    """Sankey 다이어그램으로 충격 전파 경로 시각화"""
    if not paths:
        return go.Figure()

    # 노드 수집
    all_nodes = set()
    for p in paths:
        all_nodes.add(p["from"])
        all_nodes.add(p["to"])
    nodes = list(all_nodes)
    node_idx = {n: i for i, n in enumerate(nodes)}

    sources = [node_idx[p["from"]] for p in paths]
    targets = [node_idx[p["to"]] for p in paths]
    values = [abs(p["value"]) * 10 + 1 for p in paths]  # 스케일링
    labels = [p.get("mechanism", "") for p in paths]

    fig = go.Figure(go.Sankey(
        node=dict(
            pad=20, thickness=20,
            label=nodes,
            color=[COLORS["energy"] if "유가" in n or "LNG" in n or "에너지" in n
                   else COLORS["agriculture"] if "곡물" in n or "비료" in n or "사료" in n
                   else COLORS["finance"] if "금리" in n or "신용" in n
                   else "#888" for n in nodes],
        ),
        link=dict(
            source=sources, target=targets, value=values,
            label=labels,
            color="rgba(255,255,255,0.15)",
        ),
    ))

    fig.update_layout(
        title=title,
        template="plotly_dark",
        paper_bgcolor=COLORS["bg_dark"],
        height=500,
        margin=dict(l=20, r=20, t=50, b=20),
    )
    return fig


def gauge_chart(value: float, title: str, max_val: float = 1.0) -> go.Figure:
    """게이지 차트 (확률 표시용)"""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value * 100,
        title={"text": title, "font": {"size": 14}},
        number={"suffix": "%", "font": {"size": 24}},
        gauge={
            "axis": {"range": [0, max_val * 100]},
            "bar": {"color": COLORS["energy"]},
            "steps": [
                {"range": [0, 10], "color": "#1a472a"},
                {"range": [10, 25], "color": "#8B8000"},
                {"range": [25, 50], "color": "#8B4513"},
                {"range": [50, 100], "color": "#8B0000"},
            ],
        },
    ))

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=COLORS["bg_dark"],
        height=250,
        margin=dict(l=20, r=20, t=40, b=10),
    )
    return fig


def distribution_chart(data: list, title: str, xlabel: str = "",
                        ci: tuple = None) -> go.Figure:
    """확률 분포 히스토그램"""
    fig = go.Figure()

    fig.add_trace(go.Histogram(
        x=data, nbinsx=50,
        marker_color=COLORS["compound"],
        opacity=0.7,
        name="분포",
    ))

    if ci:
        for val, label in [(ci[0], "2.5%"), (ci[1], "97.5%")]:
            fig.add_vline(x=val, line_dash="dash", line_color=COLORS["negative"],
                          annotation_text=f"{label}: {val:.2f}")

    mean_val = np.mean(data)
    fig.add_vline(x=mean_val, line_color=COLORS["positive"],
                  annotation_text=f"평균: {mean_val:.2f}")

    fig.update_layout(
        title=title,
        xaxis_title=xlabel,
        yaxis_title="빈도",
        template="plotly_dark",
        paper_bgcolor=COLORS["bg_dark"],
        plot_bgcolor=COLORS["bg_dark"],
        height=350,
        margin=dict(l=40, r=20, t=50, b=40),
    )
    return fig


def radar_chart(categories: list, values_list: list[list],
                names: list[str], title: str) -> go.Figure:
    """레이더 차트 (정책 비교용)"""
    fig = go.Figure()
    colors = [COLORS["energy"], COLORS["agriculture"], COLORS["finance"], COLORS["compound"]]

    for i, (values, name) in enumerate(zip(values_list, names)):
        fig.add_trace(go.Scatterpolar(
            r=values + [values[0]],
            theta=categories + [categories[0]],
            fill="toself",
            name=name,
            line_color=colors[i % len(colors)],
            opacity=0.6,
        ))

    fig.update_layout(
        polar=dict(bgcolor=COLORS["bg_dark"]),
        title=title,
        template="plotly_dark",
        paper_bgcolor=COLORS["bg_dark"],
        height=450,
        margin=dict(l=60, r=60, t=50, b=40),
    )
    return fig


def pie_chart(labels: list, values: list, title: str) -> go.Figure:
    """파이 차트"""
    fig = go.Figure(go.Pie(
        labels=labels, values=values,
        hole=0.4,
        textinfo="label+percent",
        marker=dict(colors=px.colors.qualitative.Set2),
    ))

    fig.update_layout(
        title=title,
        template="plotly_dark",
        paper_bgcolor=COLORS["bg_dark"],
        height=350,
        margin=dict(l=20, r=20, t=50, b=20),
    )
    return fig
