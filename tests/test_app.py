from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1]/"app.py"


def start():
    app=AppTest.from_file(str(APP),default_timeout=20).run()
    assert not app.exception
    return app


def test_default_ui_and_all_controls():
    app=start()
    assert app.metric[0].value=="2.25 倍"
    assert app.metric[1].value=="11.25 mAs"
    changes={"reference_sid":80,"changed_sid":180,"reference_mas":10.,"oid":60,"focal":2.,"dimension":30}
    for key,value in changes.items():
        app.slider(key=key).set_value(value).run()
        assert not app.exception
    assert app.metric[0].value=="5.062 倍"
    assert app.metric[1].value=="50.625 mAs"
    assert app.metric[2].value=="120.0000 mm"
    assert app.metric[3].value=="6.00000 mm"


def test_display_gain_and_zoom_do_not_change_physical_metrics():
    app=start()
    values=[m.value for m in app.metric]
    for gain in (5,10,1):
        app.selectbox(key="gain").select(gain).run()
        app.selectbox(key="view").select("右端を拡大").run()
        assert not app.exception
        assert [m.value for m in app.metric]==values
        if gain!=1:
            assert "実際のX線画像を再現したものではありません" in app.warning[0].value


def test_independent_sessions_and_common_inputs_do_not_change_factor():
    a,b=start(),start()
    a.slider(key="oid").set_value(60).run()
    a.slider(key="focal").set_value(0.).run()
    a.slider(key="dimension").set_value(30).run()
    a.selectbox(key="gain").select(10).run()
    assert a.metric[0].value=="2.25 倍"
    b.slider(key="changed_sid").set_value(80).run()
    a.run()
    assert a.slider(key="changed_sid").value==150
    assert a.metric[0].value=="2.25 倍"
    assert b.metric[0].value=="0.64 倍"
    assert b.slider(key="oid").value==20
    assert b.selectbox(key="gain").value==1
    assert not a.exception and not b.exception


@pytest.mark.parametrize("sid1,sid2,oid,focal", [(70,180,60,2.),(180,70,0,0.),(70,70,0,1.)])
def test_boundary_ui(sid1,sid2,oid,focal):
    app=start()
    for key,value in [("reference_sid",sid1),("changed_sid",sid2),("oid",oid),("focal",focal)]:
        app.slider(key=key).set_value(value)
    app.run()
    assert not app.exception


def test_different_working_directory(monkeypatch,tmp_path):
    monkeypatch.chdir(tmp_path)
    app=start()
    assert not app.exception
    assert any("計算式と単位" in m.value for m in app.markdown)
