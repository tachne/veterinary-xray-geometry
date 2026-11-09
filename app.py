"""Independent experiment screens; all widget state is per browser session."""

import streamlit as st
from views import oid, sid, terminology

st.set_page_config(page_title="撮影幾何学 v0.3.4", page_icon="📐", layout="wide")
experiments = st.tabs(("実験① SID（FFD）変更", "実験② OID変更", "用語と距離"),
                      key="experiment", on_change="rerun")
for tab, module in zip(experiments, (sid, oid, terminology)):
    # Only the selected experiment contributes controls to the sidebar.
    if tab.open:
        with tab:
            module.render()
