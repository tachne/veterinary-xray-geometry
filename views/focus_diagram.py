"""One explanatory projection figure, shared by experiments and terminology."""

import streamlit as st

from geometry.finite_focus import finite_focus_figure


def show_focus_diagram(pair, experiment, key):
    st.caption("投影図の色：濃色＝本影、黄土色＝半影、淡黄色＝X線束の模式的な外形。")
    st.plotly_chart(finite_focus_figure(pair,experiment),width="stretch",theme=None,
                    config={"displayModeBar":False,"scrollZoom":False},key=key)
    st.caption("淡黄色＝X線束の模式的な外形、濃色＝本影、黄土色＝左右の半影。"
               "上端は線状焦点、下端は検出器です。焦点両端から被写体両端を通る4本の境界線を延長して示します。")
    st.caption("本影は焦点全体が被写体に隠れる領域、半影は焦点の一部が隠れる領域です。"
               "この区分は不透過体の遮蔽幾何学です。既存の黒化度画像は透過率35％を仮定するため、本影相当部も完全な遮蔽ではありません。")
    st.caption("左右の尺度は共通です。横方向mm・深さ方向cmは別縮尺で、実空間の角度を表しません。"
               "投影図の焦点幅・半影幅は強調していません（1倍）。下段は検出器右端の拡大図で、左右共通の座標範囲です。"
               "画像のぼけ強調倍率はこの投影図へ適用しません。X線束の外縁・色・線の太さは模式表示で、照射野・線量の計算ではありません。")
