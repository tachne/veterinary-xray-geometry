"""Finite-source shadow geometry. The existing physics and image renderer are unchanged."""

from collections.abc import Mapping
from dataclasses import dataclass

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .model import Comparison, Geometry, compare, edge_intersections
from .oid import oid_comparison

BEAM = "#FFF3CF"
UMBRA = "#4C5D73"
PENUMBRA = "#E8B34B"


@dataclass(frozen=True)
class Shadow:
    left_outer: float
    left_inner: float
    right_inner: float
    right_outer: float


def shadow_edges(g: Geometry) -> Shadow:
    left, right = edge_intersections(g)
    return Shadow(min(left), max(left), min(right), max(right))


def current_comparisons(state: Mapping) -> tuple[Comparison, Comparison]:
    """Read each experiment's saved inputs; never mutate them."""
    return (compare(state.get("reference_sid", 100), state.get("changed_sid", 150),
                    state.get("oid", 20), state.get("focal", 1.),
                    state.get("dimension", 10), state.get("reference_mas", 5.)),
            oid_comparison(state.get("oid_experiment_distance", 20.),
                           reference_oid_cm=state.get("oid_reference_distance", 0.)))


def finite_focus_figure(pair: Comparison, experiment="sid") -> go.Figure:
    """Source at top, detector below; all four rays use true, unamplified coordinates.

    The pale beam envelope is illustrative, not a collimator or dose model.
    A separate shared-scale detector inset magnifies the right edge without
    multiplying the focal size, ray slopes or geometrical penumbra width.
    """
    if experiment not in ("sid", "oid"):
        raise ValueError("実験名が不正です。")
    geometries = (pair.reference, pair.changed)
    shadows = tuple(shadow_edges(g) for g in geometries)
    extent = max(s.right_outer for s in shadows)
    beam_half = max(7., extent*1.28) if experiment == "sid" else 14.
    depth = max(g.sid_cm for g in geometries)
    padding = max(.05, max(g.ug_mm for g in geometries)*.7)
    inset_range = (max(0., min(s.right_inner for s in shadows)-padding),
                   max(s.right_outer for s in shadows)+padding)
    titles = tuple(f"{label} · SID {g.sid_cm:g} cm / OID {g.oid_cm:g} cm<br>"
                   f"F {g.focal_mm:g} mm · M {g.magnification:.5f} · Ug {g.ug_mm:.5f} mm"
                   for label,g in zip(("基準条件","変更後条件"),geometries))
    fig = make_subplots(rows=2, cols=2, row_heights=[.76,.24], horizontal_spacing=.12,
                        vertical_spacing=.17,
                        subplot_titles=(*titles,"検出器面の右端（横方向を拡大）","検出器面の右端（横方向を拡大）"))

    def polygon(x, y, color, name, col, row=1, legend=False):
        fig.add_trace(go.Scatter(x=x, y=y, mode="lines", line=dict(width=0),
                                 fill="toself", fillcolor=color, name=name,
                                 showlegend=legend, hoverinfo="skip"), row=row, col=col)

    for col,(g,s) in enumerate(zip(geometries,shadows),1):
        polygon([-g.focal_mm/2,g.focal_mm/2,beam_half,-beam_half],
                [0,0,g.sid_cm,g.sid_cm],BEAM,f"beam_{col}",col)
        if g.oid_cm > 0:
            polygon([-g.object_mm/2,g.object_mm/2,s.right_inner,s.left_inner],
                    [g.sod_cm,g.sod_cm,g.sid_cm,g.sid_cm],UMBRA,f"umbra_{col}",col)
            if g.ug_mm > 0:
                polygon([-g.object_mm/2,s.left_outer,s.left_inner],
                        [g.sod_cm,g.sid_cm,g.sid_cm],PENUMBRA,f"left_penumbra_{col}",col)
                polygon([g.object_mm/2,s.right_inner,s.right_outer],
                        [g.sod_cm,g.sid_cm,g.sid_cm],PENUMBRA,f"right_penumbra_{col}",col)
        for edge,endpoints in zip((-g.object_mm/2,g.object_mm/2),edge_intersections(g)):
            for source,endpoint in zip((-g.focal_mm/2,g.focal_mm/2),endpoints):
                fig.add_trace(go.Scatter(x=[source,edge,endpoint],y=[0,g.sod_cm,g.sid_cm],
                                        mode="lines",line=dict(color="#50879A",width=1.3),
                                        name=f"ray_{col}",showlegend=False,
                                        hovertemplate="横方向 %{x:.5f} mm<br>焦点から %{y:.5f} cm<extra>境界線</extra>"),row=1,col=col)
        # Detector plane, then its physically sized shadow intervals.
        fig.add_trace(go.Scatter(x=[-beam_half,beam_half],y=[g.sid_cm]*2,mode="lines",
                                line=dict(color="#8992A0",width=3),name=f"detector_{col}",
                                showlegend=False,hoverinfo="skip"),row=1,col=col)
        for name,lo,hi,color in (("umbra",s.left_inner,s.right_inner,UMBRA),
                                 ("left_penumbra",s.left_outer,s.left_inner,PENUMBRA),
                                 ("right_penumbra",s.right_inner,s.right_outer,PENUMBRA)):
            if hi > lo:
                fig.add_trace(go.Scatter(x=[lo,hi],y=[g.sid_cm]*2,mode="lines",
                                        line=dict(color=color,width=9),name=f"detector_{name}_{col}",
                                        showlegend=False,hovertemplate=f"区間幅 {hi-lo:.5f} mm<extra></extra>"),row=1,col=col)
        for x,y,name,color in (([-g.focal_mm/2,g.focal_mm/2],0,"focus","#B94C78"),
                              ([-g.object_mm/2,g.object_mm/2],g.sod_cm,"object","#304D63")):
            point = name == "focus" and g.focal_mm == 0
            fig.add_trace(go.Scatter(x=[0] if point else x,y=[y] if point else [y,y],
                                    mode="markers" if point else "lines",marker=dict(size=7,color=color),
                                    line=dict(color=color,width=7),name=f"{name}_{col}",
                                    showlegend=False,hoverinfo="skip"),row=1,col=col)
        fig.add_annotation(x=0,y=0,text="点焦点 F = 0 mm" if g.focal_mm==0 else f"線状焦点 F = {g.focal_mm:g} mm",
                           showarrow=False,yshift=17,row=1,col=col)
        if g.oid_cm > 0:
            fig.add_annotation(x=0,y=g.sod_cm,text="被写体",showarrow=False,yshift=12,row=1,col=col)
            if g.oid_cm/depth >= .06:
                fig.add_annotation(x=0,y=(g.sod_cm+g.sid_cm)/2,text="本影",showarrow=False,
                                   font=dict(color="white",size=12),row=1,col=col)
        fig.add_annotation(x=0,y=g.sid_cm,text="被写体・検出器" if g.oid_cm==0 else "検出器",
                           showarrow=False,yshift=-19,row=1,col=col)
        # Distance bars are on the same physical depth axis as the rays.
        for name,x,start,end in (("SID（FFD）",beam_half*1.28,0,g.sid_cm),
                                 ("SOD",-beam_half*1.28,0,g.sod_cm),
                                 ("OID",-beam_half*1.28,g.sod_cm,g.sid_cm)):
            fig.add_trace(go.Scatter(x=[x,x],y=[start,end],mode="lines+markers",
                                    line=dict(color="#909AAA",width=1),marker=dict(symbol="line-ew",size=9),
                                    name=f"distance_{name}_{col}",showlegend=False,hoverinfo="skip"),row=1,col=col)
            fig.add_annotation(x=x,y=(start+end)/2,text=f"{name} {end-start:g} cm",
                               textangle=90 if name.startswith("SID") else -90,
                               showarrow=False,xshift=13 if x>0 else -13,
                               font=dict(size=11),row=1,col=col)
        # The inset uses absolute detector coordinates, shared between the two conditions.
        lo,hi = inset_range
        polygon([lo,hi,hi,lo],[0,0,1,1],BEAM,f"inset_beam_{col}",col,row=2)
        for name,a,b,color in (("umbra",lo,min(hi,s.right_inner),UMBRA),
                               ("penumbra",max(lo,s.right_inner),min(hi,s.right_outer),PENUMBRA)):
            if b > a:
                polygon([a,b,b,a],[0,0,1,1],color,f"inset_{name}_{col}",col,row=2)
        for edge in (s.right_inner,s.right_outer):
            fig.add_vline(x=edge,line_width=1,line_color="#8992A0",row=2,col=col)
        fig.add_annotation(x=(s.right_inner+s.right_outer)/2,y=1.13,
                           text=f"半影 Ug = {g.ug_mm:.5f} mm",showarrow=False,row=2,col=col)
        fig.update_xaxes(range=[-beam_half*1.60,beam_half*1.60],title="横方向 (mm)",fixedrange=True,row=1,col=col)
        fig.update_yaxes(range=[depth*1.14,-depth*.12],title="焦点からの距離 (cm)" if col==1 else None,
                         fixedrange=True,row=1,col=col)
        fig.update_xaxes(range=inset_range,title="検出器上の位置 (mm)",fixedrange=True,row=2,col=col)
        fig.update_yaxes(range=[-.05,1.5],visible=False,fixedrange=True,row=2,col=col)
    fig.update_layout(height=760,margin=dict(l=60,r=20,t=80,b=45),template="plotly_white",
                      font=dict(size=12),showlegend=False,
                      meta=dict(experiment=experiment,penumbra_gain=1,
                                reference=dict(sid_cm=pair.reference.sid_cm,oid_cm=pair.reference.oid_cm,
                                               focal_mm=pair.reference.focal_mm,ug_mm=pair.reference.ug_mm),
                                changed=dict(sid_cm=pair.changed.sid_cm,oid_cm=pair.changed.oid_cm,
                                             focal_mm=pair.changed.focal_mm,ug_mm=pair.changed.ug_mm)))
    return fig
