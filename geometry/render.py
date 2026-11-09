"""Analytic 1-D uniform-source shadow and shared-scale Plotly figures.

No detector blur, pixel aperture, stochastic noise, or clinical anatomy model.
"""

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .model import Comparison, Geometry, edge_intersections
from .exposure import calculate_exposure
from .film_display import film_brightness, validate_tone_gain

GAINS = (1, 5, 10)
VIEWS = ("全体", "右端を拡大")
COLORS = ("#167D9A", "#B96626")


def display_settings(gain: int, view: str) -> None:
    if isinstance(gain, bool) or gain not in GAINS or view not in VIEWS:
        raise ValueError("表示設定が不正です。")


def transmission(x_mm, projection_mm: float, ug_mm: float) -> np.ndarray:
    """Relative primary fluence through an opaque strip with a uniform line source.

    The rectangle/box overlap is analytic: Ug is the FULL edge ramp width,
    not a Gaussian standard deviation. Point-source endpoints use the half value.
    """
    if not np.isfinite(projection_mm) or projection_mm <= 0:
        raise ValueError("投影寸法は正の有限値が必要です。")
    if not np.isfinite(ug_mm) or ug_mm < 0:
        raise ValueError("半影幅は非負の有限値が必要です。")
    x = np.asarray(x_mm, dtype=float)
    if not np.all(np.isfinite(x)):
        raise ValueError("描画座標は有限値が必要です。")
    half = projection_mm / 2
    if ug_mm == 0:
        return np.where(np.abs(x) < half, 0.0, np.where(np.abs(x) == half, 0.5, 1.0))
    overlap = np.clip(np.minimum(x + ug_mm / 2, half)
                      - np.maximum(x - ug_mm / 2, -half), 0, ug_mm)
    return np.clip(1 - overlap / ug_mm, 0, 1)


def common_range(c: Comparison, gain: int, view: str) -> tuple[float, float]:
    display_settings(gain, view)
    geometries = (c.reference, c.changed)
    if view == "全体":
        extent = max((g.projection_mm + g.ug_mm * gain) / 2 for g in geometries)
        return (-extent * 1.18 - .5, extent * 1.18 + .5)
    edges = [g.projection_mm / 2 for g in geometries]
    padding = max(.35, max(g.ug_mm * gain for g in geometries) * .8)
    return (min(edges) - padding, max(edges) + padding)


def profile_coordinates(g: Geometry, x_range, gain: int) -> np.ndarray:
    # Include exact ramp breakpoints, even when Ug is smaller than the grid step.
    p, u = g.projection_mm, g.ug_mm * gain
    anchors = [(sign * p + shift * u) / 2 for sign in (-1, 1) for shift in (-1, 1)]
    if u == 0:
        eps = (x_range[1] - x_range[0]) * 1e-10
        anchors += [edge + offset for edge in (-p / 2, p / 2) for offset in (-eps, eps)]
    anchors = [v for v in anchors if x_range[0] <= v <= x_range[1]]
    return np.unique(np.concatenate((np.linspace(*x_range, 801), anchors)))


def projection_figure(c: Comparison, gain=1, view="全体", *, changed_mas=5.0, tone_gain=1) -> go.Figure:
    display_settings(gain, view)
    validate_tone_gain(tone_gain)
    exposure = calculate_exposure(c, changed_mas)
    limits = common_range(c, gain, view)
    fig = make_subplots(rows=2, cols=2, row_heights=[.28, .72],
                        horizontal_spacing=.11, vertical_spacing=.14,
                        subplot_titles=(
                            f"基準 · {c.reference.sid_cm:g} cm / {c.reference_mas:g} mAs<br>相対線量 {exposure.reference_relative_dose:.5f}",
                            f"変更後 · {c.changed.sid_cm:g} cm / {changed_mas:g} mAs<br>相対線量 {exposure.changed_relative_dose:.5f}"))
    grid = np.linspace(*limits, 2049)
    doses = (exposure.reference_relative_dose, exposure.changed_relative_dose)
    for col, (g, color, dose) in enumerate(zip((c.reference, c.changed), COLORS, doses), 1):
        u_display = g.ug_mm * gain
        signal = film_brightness(transmission(grid, g.projection_mm, u_display), dose, tone_gain)
        fig.add_trace(go.Heatmap(x=grid, y=[0, 1], z=np.tile(signal, (2, 1)),
                                zmin=0, zmax=1, showscale=False,
                                colorscale=[[0, "#000000"], [1, "#FFFFFF"]],
                                zsmooth=False, hoverinfo="skip", name=f"strip_{col}"), row=1, col=col)
        x = profile_coordinates(g, limits, gain)
        fig.add_trace(go.Scatter(x=x, y=film_brightness(transmission(x, g.projection_mm, u_display), dose, tone_gain),
                                line=dict(color=color, width=2.5), name=f"profile_{col}",
                                hovertemplate="位置 %{x:.4f} mm<br>表示明度 %{y:.4f}<extra></extra>"),
                      row=2, col=col)
        # Centre-source projected edges remain fixed when display gain changes.
        for edge in (-g.projection_mm / 2, g.projection_mm / 2):
            if limits[0] <= edge <= limits[1]:
                fig.add_vline(x=edge, line_dash="dot", line_color=color, line_width=1,
                              row=2, col=col)
        edge = g.projection_mm / 2
        fig.add_shape(type="rect", x0=edge-u_display/2, x1=edge+u_display/2,
                      y0=0, y1=1, fillcolor=color, opacity=.12, line_width=0,
                      row=2, col=col)
        fig.update_xaxes(range=list(limits), fixedrange=True, row=1, col=col, showticklabels=False)
        fig.update_xaxes(range=list(limits), fixedrange=True, title_text="検出器上の位置 (mm)", row=2, col=col)
        fig.update_yaxes(range=[-.5, 1.5], fixedrange=True, visible=False, row=1, col=col)
        fig.update_yaxes(range=[-.05, 1.05], fixedrange=True, tickvals=[0, .5, 1],
                         title_text="表示明度（0黒・1白）" if col == 1 else None, row=2, col=col)
    fig.update_layout(height=500, margin=dict(l=55, r=20, t=75, b=40),
                      showlegend=False, template="plotly_white", font=dict(size=13),
                      meta=dict(display_gain=gain, tone_gain=tone_gain, view=view, common_range=limits))
    return fig


def geometry_figure(c: Comparison) -> go.Figure:
    """Longitudinal cm and transverse mm axes are independently scaled, both shared."""
    geometries = (c.reference, c.changed)
    xmax = max(g.sid_cm for g in geometries) * 1.07
    ymax = max((g.projection_mm + g.ug_mm) / 2 for g in geometries) * 1.3 + 1
    fig = make_subplots(rows=1, cols=2, horizontal_spacing=.12,
                        subplot_titles=("基準条件", "変更後条件"))
    for col, (g, color) in enumerate(zip(geometries, COLORS), 1):
        for edge, endpoints in zip((-g.object_mm/2, g.object_mm/2), edge_intersections(g)):
            for source, endpoint in zip((-g.focal_mm/2, g.focal_mm/2), endpoints):
                fig.add_trace(go.Scatter(x=[0, g.sod_cm, g.sid_cm],
                                        y=[source, edge, endpoint], mode="lines",
                                        line=dict(color=color, width=1), opacity=.7,
                                        name=f"ray_{col}", hovertemplate="軸方向 %{x:.3f} cm<br>横方向 %{y:.4f} mm<extra></extra>"), row=1, col=col)
            lo, hi = sorted(endpoints)
            fig.add_trace(go.Scatter(x=[g.sid_cm, g.sid_cm], y=[lo, hi],
                                    mode="lines", line=dict(color="#D59A18", width=9),
                                    name=f"penumbra_{col}",
                                    hovertemplate=f"検出器面 Ug = {g.ug_mm:.5f} mm<extra></extra>"), row=1, col=col)
        items = [(0, -g.focal_mm/2, g.focal_mm/2, "焦点", "#9C4974"),
                 (g.sod_cm, -g.object_mm/2, g.object_mm/2, "被写体", color),
                 (g.sid_cm, -ymax*.9, ymax*.9, "検出器", "#7D8796")]
        for x, lo, hi, label, shade in items:
            fig.add_trace(go.Scatter(x=[x, x], y=[lo, hi], mode="lines+markers",
                                    marker=dict(size=4), line=dict(color=shade, width=4),
                                    name=label, hoverinfo="name"), row=1, col=col)
        # The object and detector coincide at OID=0; the combined label avoids overlap.
        labels = [(0, "焦点"), (g.sid_cm, "被写体・検出器" if g.oid_cm == 0 else "検出器")]
        if g.oid_cm != 0:
            labels.append((g.sod_cm, "被写体"))
        for x, label in labels:
            fig.add_annotation(x=x, y=ymax*.95, text=label, showarrow=False,
                               yshift=5 if label != "被写体" else -20, row=1, col=col)
        fig.update_xaxes(range=[-xmax*.04, xmax], fixedrange=True,
                         title_text="焦点からの距離 (cm)", row=1, col=col)
        fig.update_yaxes(range=[-ymax, ymax*1.12], fixedrange=True,
                         title_text="横方向 (mm)" if col == 1 else None, row=1, col=col)
    fig.update_layout(height=420, margin=dict(l=55, r=20, t=45, b=40),
                      showlegend=False, template="plotly_white", font=dict(size=13))
    return fig
