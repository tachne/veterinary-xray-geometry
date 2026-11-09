"""Independent OID pair; no exposure controls and fixed interior/background tones."""

import streamlit as st

from geometry import APP_VERSION
from geometry.oid import oid_comparison, oid_projection_figure
from views.focus_diagram import show_focus_diagram
from geometry.render import GAINS, VIEWS


def render():
    st.title("OIDと幾何学的半影")
    st.caption(f"Veterinary Radiographic Geometry Simulator · v{APP_VERSION} · OID独立実験")
    with st.sidebar:
        st.header("OID独立実験")
        reference_oid = st.slider("基準OID (cm)", 0.0, 50.0, 0.0, .1,
                                   key="oid_reference_distance", persist_state="session")
        changed_oid = st.slider("変更後OID (cm)", 0.0, 50.0, 20.0, .1,
                                 key="oid_experiment_distance", persist_state="session")
        st.markdown("固定条件：\n\n- SID：100 cm\n- 実効焦点サイズ F：1.0 mm\n- 被写体実寸法：10 mm")
        st.caption("基準OIDと変更後OIDは独立して設定できます。焦点と画像受像面は固定です。")
    pair = oid_comparison(changed_oid, reference_oid_cm=reference_oid)
    for col, label, g in zip(st.columns(2), ("基準", "変更後"), (pair.reference, pair.changed)):
        with col:
            st.subheader(f"{label} · OID {g.oid_cm:g} cm")
            first, second = st.columns(2)
            first.metric("SOD", f"{g.sod_cm:g} cm")
            second.metric("拡大率 M", f"{g.magnification:.5f}")
            first.metric("投影寸法", f"{g.projection_mm:.4f} mm")
            second.metric("幾何学的不鋭 Ug", f"{g.ug_mm:.5f} mm")
            st.caption(f"SOD = SID − OID = 100 − {g.oid_cm:g} = {g.sod_cm:g} cm")
    st.info("両画像の背景と被写体内部の黒化度（表示濃淡）を固定しています。"
            "幾何学的影響を独立して示す教育上の仮定であり、実機の検出器信号が完全に一定であることを意味しません。")
    a, b = st.columns(2)
    gain = a.selectbox("OID実験：半影の表示倍率", GAINS,
                       format_func=lambda x: "標準（1倍）" if x == 1 else f"教育用 {x}倍強調",
                       key="oid_display_gain", persist_state="session")
    view = b.selectbox("OID実験：共通表示範囲", VIEWS,
                       key="oid_display_view", persist_state="session")
    if gain != 1:
        st.warning(f"教育用の視覚的強調：表示用の半影幅を{gain}倍にしています。計算上のUg・M・投影寸法は変わりません。")
    st.plotly_chart(oid_projection_figure(changed_oid, gain, view, reference_oid_cm=reference_oid),
                    width="stretch", theme=None,
                    config={"displayModeBar": False, "scrollZoom": False}, key="oid_projection_chart")
    st.caption("v0.2の半影形状を再利用しています。左右は同じ尺度・固定階調です。"
               "OIDに伴う拡大と境界の半影だけを表示し、線量や黒化度の変化は扱いません。"
               "画面の縮小・補間は物理的な不鋭ではありません。")
    with st.expander("撮影配置・距離の関係"):
        show_focus_diagram(pair, "oid", "oid_geometry_chart")
    st.latex(r"M=\frac{SID}{SID-OID},\qquad P=D\,M,\qquad U_g=F\frac{OID}{SID-OID}")
    st.caption("SID > OID ≥ 0。Ugは検出器面の半影全幅です。用語の意味は「用語と距離」で確認できます。")
