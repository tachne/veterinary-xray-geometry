"""Streamlit entrypoint. All student state is local to each Streamlit session."""

from pathlib import Path

import streamlit as st

from geometry import APP_VERSION, MODEL_VERSION
from geometry.export import csv_bytes
from geometry.model import compare
from geometry.exposure import calculate_exposure, CHANGED_MAS_MIN, CHANGED_MAS_MAX
from geometry.film_display import TONE_GAINS
from geometry.render import GAINS, VIEWS, projection_figure
from views.focus_diagram import show_focus_diagram

ROOT = Path(__file__).resolve().parents[1]


def render():
    st.title("撮影幾何学・黒化度")
    st.caption(f"Veterinary Radiographic Geometry Simulator · v{APP_VERSION} · 理想化モデル")
    st.write("SID（FFD）とmAsを変え、拡大・半影とフィルム黒化度の方向を比較します。")

    with st.sidebar:
        st.header("撮影条件")
        reference_sid = st.slider("基準SID (cm)", 70, 180, 100, key="reference_sid", persist_state="session")
        changed_sid = st.slider("変更後SID (cm)", 70, 180, 150, key="changed_sid", persist_state="session")
        reference_mas = st.slider("基準mAs (mAs)", 1.0, 20.0, 5.0, .5, key="reference_mas", persist_state="session")
        changed_mas = st.number_input("変更後mAs (mAs)", CHANGED_MAS_MIN, CHANGED_MAS_MAX,
                                      5.0, .25, format="%.5f", key="changed_mas", persist_state="session")
        st.caption("変更後mAsは手動入力です。SIDや基準mAsを変更しても自動補正しません。")
        st.divider()
        st.subheader("両条件に共通")
        oid = st.slider("OID (cm)", 0, 60, 20, key="oid", persist_state="session")
        focal = st.slider("実効焦点サイズ F (mm)", 0.0, 2.0, 1.0, .1, key="focal", persist_state="session")
        dimension = st.slider("被写体実寸法 (mm)", 5, 30, 10, key="dimension", persist_state="session")
        st.caption("SID > OID ≥ 0。実寸法は中心軸と直交する方向の長さです。")

    try:
        comparison = compare(reference_sid, changed_sid, oid, focal, dimension, reference_mas)
        exposure = calculate_exposure(comparison, changed_mas)
    except ValueError as exc:
        st.error(str(exc))
        st.stop()

    with st.container(border=True):
        st.subheader(f"SID {reference_sid} → {changed_sid} cm のmAs補正")
        factor_col, mas_col = st.columns(2)
        factor_col.metric("mAs補正倍率", f"{comparison.correction_factor:.4g} 倍")
        mas_col.metric("同等線量にする理論mAs", f"{comparison.changed_mas:.6g} mAs")
        st.caption(f"({changed_sid} / {reference_sid})² × {reference_mas:g} mAs。"
                   "補正倍率はSIDの組だけで決まり、OID・焦点サイズ・被写体寸法・基準mAsには依存しません。")
    st.info("教育用のフィルム黒化度模式表示です。実際のフィルム特性曲線やDR画像の表示輝度を再現しません。"
            "同一管電圧・線質・透過率を仮定します。理論mAsは入力に自動適用せず、実機の条件を推奨しません。")

    for col, label, g, mas, dose in zip(st.columns(2), ("基準条件", "変更後条件"),
                             (comparison.reference, comparison.changed),
                             (reference_mas, changed_mas),
                             (exposure.reference_relative_dose, exposure.changed_relative_dose)):
        with col:
            st.subheader(f"{label} · {g.sid_cm:g} cm / {mas:g} mAs")
            st.markdown(f"相対検出器入射線量 **{dose:.5f}**（直接照射領域）")
            st.markdown(f"SOD **{g.sod_cm:g} cm**　｜　拡大率 M **{g.magnification:.5f}**")
            a, b = st.columns(2)
            a.metric("投影寸法", f"{g.projection_mm:.4f} mm")
            b.metric("幾何学的不鋭 Ug", f"{g.ug_mm:.5f} mm")

    st.caption(f"相対線量の固定基準：SID100 cm・5 mAs＝1。変更後 / 基準＝{exposure.changed_to_reference_ratio:.5f}。"
               "相対線量は患者線量ではありません。画像ごとの自動階調補正は行いません。")

    image_tab, geometry_tab, model_tab = st.tabs(["投影像を比較", "撮影配置", "モデル・CSV"])
    with image_tab:
        a, b, d = st.columns(3)
        gain = a.selectbox("半影の表示倍率", GAINS,
                           format_func=lambda x: "標準（1倍）" if x == 1 else f"教育用 {x}倍強調",
                           key="gain", persist_state="session")
        view = b.selectbox("両画像の表示範囲", VIEWS, key="view", persist_state="session")
        tone_gain = d.selectbox("濃淡の表示係数", TONE_GAINS, key="tone_gain", persist_state="session")
        if gain != 1:
            st.warning(f"教育用の視覚的強調：表示用半影幅だけを{gain}倍にしています。"
                       "計算値・投影寸法・mAs補正は不変です。実際のX線画像を再現したものではありません。")
        if tone_gain != 1:
            st.caption(f"濃淡の表示係数{tone_gain}：左右の表示変換に共通で適用します。線量・mAs・幾何学計算は変えません。")
        st.plotly_chart(projection_figure(comparison, gain, view, changed_mas=changed_mas, tone_gain=tone_gain), width="stretch", theme=None,
                        config={"displayModeBar": False, "scrollZoom": False}, key="projection_chart")
        st.caption("上：X線を減弱させる四角形と、直接照射領域の背景。四角形の透過率は仮定値35％です。"
                   "下：表示明度の断面（0＝黒、1＝白）。"
                   "点線＝中心焦点による投影端、着色域＝右端の表示用半影幅。左右は同一座標範囲・同一階調です。")
        st.caption("同等の線量では背景・被写体内部の濃淡が一致しますが、SIDによる投影寸法と半影の差は残ります。"
                   "一様な線状焦点を仮定した1次元モデルです。表示の画素数・画面の拡大縮小は物理的な不鋭や検出器分解能ではありません。"
                   "微小な半影は「右端を拡大」で確認できます。量子ノイズ・検出器ぼけ・動きは含みません。")
    with geometry_tab:
        show_focus_diagram(comparison, "sid", "geometry_chart")
    with model_tab:
        st.subheader("現在の2条件を保存")
        st.download_button("計算結果をCSVで保存", csv_bytes(comparison, gain, view, changed_mas=changed_mas, tone_gain=tone_gain),
                           "radiographic_geometry_comparison.csv", "text/csv", key="download_csv")
        st.caption("基準・変更後の2行。単位付き列名で全入力・計算値・表示設定・モデル版を保存します。"
                   "changed_masは手入力値、theoretical_changed_masは理論補正値です。Ugは強調前の理論値です。"
                   "入力や操作履歴をアプリ独自の共有ファイルに保存しません。")
        st.markdown((ROOT / "docs" / "physics_model.md").read_text(encoding="utf-8"))
    st.caption(f"計算モデル {MODEL_VERSION} · 教員確認用試作版")
