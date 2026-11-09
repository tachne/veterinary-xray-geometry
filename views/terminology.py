"""Distance terminology shared by the two experiments."""

import streamlit as st

from geometry import APP_VERSION
from geometry.finite_focus import current_comparisons
from views.focus_diagram import show_focus_diagram

TERMS = (
    ("SID", "Source-to-Image Receptor Distance", "X線焦点から画像受像面までの距離。"),
    ("FFD", "Focus-to-Film Distance", "X線焦点からフィルム面までの距離。従来のフィルム撮影で使用された用語。"),
    ("OID", "Object-to-Image Receptor Distance", "被写体から画像受像面までの距離。"),
    ("SOD", "Source-to-Object Distance", "X線焦点から被写体までの距離。"),
)


def render():
    st.title("用語と距離")
    st.caption(f"v{APP_VERSION} · 有限焦点・本影・半影の投影図")
    st.markdown("| 記号 | 英語表記 | 意味 |\n|---|---|---|\n" +
                "\n".join(f"| {term} | {english} | {definition} |" for term,english,definition in TERMS))
    st.info("今回のモデルではSIDとFFDは同一の幾何学的距離を指します。画像受像面をフィルム面とみなす場合の呼び方の違いです。")
    st.latex(r"SID=SOD+OID,\qquad SOD=SID-OID")
    st.caption("各実験の現在の設定を、実験画面と同じ投影図で表示します。未操作の実験は初期値を使います。設定変更は各実験タブで行います。")
    try:
        sid_pair, oid_pair = current_comparisons(st.session_state)
    except ValueError as exc:
        st.error(str(exc))
        return
    for title, pair, kind in (("SID変更実験の投影幾何学", sid_pair, "sid"),
                              ("OID変更実験の投影幾何学", oid_pair, "oid")):
        st.subheader(title)
        for label, g in (("基準",pair.reference),("変更後",pair.changed)):
            st.markdown(f"**{label}**：SID {g.sid_cm:g} cm ／ OID {g.oid_cm:g} cm ／ "
                        f"SOD {g.sod_cm:g} cm（{g.sid_cm:g} − {g.oid_cm:g}）")
        show_focus_diagram(pair, kind, f"terms_{kind}_geometry_chart")
