"""Fixed-SID OID experiment, reusing the unchanged v0.2 image renderer."""

import plotly.graph_objects as go

from .model import Comparison, Geometry, bounded, calculate_geometry, edge_intersections
from .render import projection_figure

FIXED_SID_CM = 100.0
FIXED_FOCAL_MM = 1.0
FIXED_OBJECT_MM = 10.0
MAX_OID_CM = 50.0


def oid_comparison(oid_cm: float, *, reference_oid_cm: float = 0) -> Comparison:
    bounded("基準OID (cm)", reference_oid_cm, 0, MAX_OID_CM)
    bounded("変更後OID (cm)", oid_cm, 0, MAX_OID_CM)
    reference = calculate_geometry(FIXED_SID_CM, reference_oid_cm, FIXED_FOCAL_MM, FIXED_OBJECT_MM)
    changed = calculate_geometry(FIXED_SID_CM, oid_cm, FIXED_FOCAL_MM, FIXED_OBJECT_MM)
    # Fixed normalization for the shared renderer, not an exposure experiment.
    return Comparison(reference, changed, 5.0, 1.0, 5.0)


def oid_projection_figure(oid_cm: float, gain=1, view="全体", *, reference_oid_cm: float = 0) -> go.Figure:
    c = oid_comparison(oid_cm, reference_oid_cm=reference_oid_cm)
    fig = projection_figure(c, gain, view, changed_mas=5.0, tone_gain=1)
    fig.layout.annotations[0].text = f"基準 · OID {reference_oid_cm:g} cm"
    fig.layout.annotations[1].text = f"変更後 · OID {oid_cm:g} cm"
    fig.update_yaxes(title_text="表示値（固定階調）", row=2, col=1)
    return fig


def distance_figure(g: Geometry) -> go.Figure:
    """Fixed coordinates preserve source/detector positions as OID changes."""
    expected = oid_comparison(g.oid_cm).changed
    if g != expected:
        raise ValueError("距離図はSID100 cm・焦点1 mm・実寸法10 mmの独立実験専用です。")
    fig = go.Figure()
    for edge, endpoints in zip((-g.object_mm/2, g.object_mm/2), edge_intersections(g)):
        for source, endpoint in zip((-g.focal_mm/2, g.focal_mm/2), endpoints):
            fig.add_trace(go.Scatter(x=[0, g.sod_cm, g.sid_cm], y=[source, edge, endpoint],
                                    mode="lines", line=dict(color="#167D9A", width=1),
                                    name="投影線", hovertemplate="焦点から %{x:.3f} cm<br>横方向 %{y:.4f} mm<extra></extra>"))
        fig.add_trace(go.Scatter(x=[g.sid_cm, g.sid_cm], y=sorted(endpoints), mode="lines",
                                line=dict(color="#D59A18", width=9), name="半影",
                                hovertemplate=f"Ug = {g.ug_mm:.5f} mm<extra></extra>"))
    for x, lo, hi, name, color in [
        (g.sid_cm, -11.5, 11.5, "画像受像面", "#7D8796"),
        (0, -g.focal_mm/2, g.focal_mm/2, "X線焦点", "#9C4974"),
        (g.sod_cm, -g.object_mm/2, g.object_mm/2, "被写体", "#167D9A"),
    ]:
        fig.add_trace(go.Scatter(x=[x, x], y=[lo, hi], mode="lines+markers",
                                line=dict(color=color, width=4), marker=dict(size=4),
                                name=name, hoverinfo="name"))
    spans = [(0, g.sod_cm, -13, "SOD", "#167D9A"),
             (g.sod_cm, g.sid_cm, -13, "OID", "#B96626"),
             (0, g.sid_cm, -17, "SID（＝FFD）", "#50705A")]
    for start, end, y, label, color in spans:
        fig.add_trace(go.Scatter(x=[start, end], y=[y, y], mode="lines+markers",
                                line=dict(color=color, width=2), marker=dict(symbol="line-ns", size=11),
                                name=label, hoverinfo="skip"))
        fig.add_annotation(x=(start+end)/2, y=y+1.1, text=f"{label} = {end-start:g} cm",
                           showarrow=False, font=dict(color=color, size=13))
    labels = [(0, "X線焦点"), (g.sid_cm, "被写体・画像受像面" if g.oid_cm == 0 else "画像受像面")]
    if g.oid_cm != 0:
        labels.append((g.sod_cm, "被写体"))
    for x, label in labels:
        fig.add_annotation(x=x, y=13, text=label, showarrow=False,
                           yshift=-22 if label == "被写体" else 0)
    fig.update_layout(height=390, margin=dict(l=55, r=25, t=20, b=40),
                      template="plotly_white", showlegend=False, font=dict(size=13),
                      xaxis=dict(range=[-8,108], title="焦点からの距離 (cm)", fixedrange=True),
                      yaxis=dict(range=[-19,15], title="横方向 (mm)", tickvals=[-10,0,10], fixedrange=True))
    return fig
