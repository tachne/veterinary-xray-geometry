import csv
import io

import numpy as np
import pytest
from streamlit.testing.v1 import AppTest
from pathlib import Path

from geometry.exposure import calculate_exposure, relative_dose
from geometry.export import csv_bytes
from geometry.film_display import film_brightness, OBJECT_TRANSMISSION
from geometry.model import compare
from geometry.render import projection_figure, geometry_figure


@pytest.mark.parametrize("sid,mas,expected,direction", [
    (150,5,4/9,"lighter"), (80,5,25/16,"darker"), (150,11.25,1,"equal")])
def test_requested_exposure_and_both_regions(sid,mas,expected,direction):
    c=compare(changed_sid_cm=sid)
    e=calculate_exposure(c,mas)
    assert e.reference_relative_dose==1
    assert e.changed_relative_dose==pytest.approx(expected)
    base=film_brightness([0,1],e.reference_relative_dose)
    changed=film_brightness([0,1],e.changed_relative_dose)
    if direction=="lighter":
        assert np.all(changed>base)
    elif direction=="darker":
        assert np.all(changed<base)
    else:
        np.testing.assert_allclose(changed,base,rtol=1e-14)
    assert base[0]>base[1] and changed[0]>changed[1]


@pytest.mark.parametrize("mas", [.1,1,5,11.25,20,150])
@pytest.mark.parametrize("tone", [1,2,3])
def test_object_brighter_and_both_regions_respond_without_autonormalization(mas,tone):
    for sid in (70,100,180):
        dose=relative_dose(sid,mas)
        b=film_brightness([0,1],dose,tone)
        assert 0 < b[1] < b[0] < 1
        darker=film_brightness([0,1],dose*1.1,tone)
        assert np.all(darker<b)
        np.testing.assert_allclose(b,[1/(1+tone*dose*OBJECT_TRANSMISSION),1/(1+tone*dose)])


def test_both_heatmap_plateaux_change_and_fixed_grayscale():
    base=projection_figure(compare(changed_sid_cm=100),changed_mas=5)
    reference=np.array(base.data[0].z)[0]
    for sid,mas,sign in [(150,5,1),(80,5,-1),(150,11.25,0)]:
        fig=projection_figure(compare(changed_sid_cm=sid),changed_mas=mas)
        maps=[t for t in fig.data if t.type=="heatmap"]
        a,b=(np.asarray(t.z)[0] for t in maps)
        # Same physical x grid in the pair. Sample outside object and its centre.
        for idx in (0,len(a)//2):
            if sign:
                assert sign*(b[idx]-a[idx])>0
            else:
                assert b[idx]==pytest.approx(a[idx])
            assert a[idx]==pytest.approx(reference[idx])
        assert maps[0].zmin==maps[1].zmin==0
        assert maps[0].zmax==maps[1].zmax==1
        assert maps[0].colorscale==maps[1].colorscale==((0,"#000000"),(1,"#FFFFFF"))


def test_compensation_equal_entire_image_only_when_geometry_also_matches():
    c=compare(oid_cm=0)
    fig=projection_figure(c,changed_mas=11.25)
    np.testing.assert_allclose(fig.data[0].z,fig.data[2].z)


def test_manual_mas_does_not_change_geometry_or_theoretical_correction():
    c=compare()
    original=geometry_figure(c).to_json()
    for mas in (.1,5,11.25,150):
        e=calculate_exposure(c,mas)
        projection_figure(c,changed_mas=mas)
        assert e.changed_mas==mas
        assert c.changed_mas==11.25  # Existing model field holds theoretical correction.
        assert c.correction_factor==2.25
        assert geometry_figure(c).to_json()==original


def test_fixed_reference_unit_and_independent_inputs():
    for reference_mas in (1,5,20):
        c=compare(reference_mas=reference_mas)
        e=calculate_exposure(c,5)
        assert e.reference_relative_dose==reference_mas/5
        assert e.changed_relative_dose==pytest.approx(4/9)
        assert e.changed_to_reference_ratio==pytest.approx((4/9)/(reference_mas/5))


def test_display_settings_leave_exposure_and_physical_csv_identical():
    c=compare()
    results=[]
    for gain,tone,view in [(1,1,"全体"),(5,2,"右端を拡大"),(10,3,"全体")]:
        projection_figure(c,gain,view,changed_mas=11.25,tone_gain=tone)
        rows=list(csv.DictReader(io.StringIO(csv_bytes(c,gain,view,changed_mas=11.25,tone_gain=tone).decode("utf-8-sig"))))
        for row in rows:
            assert row.pop("display_penumbra_gain")==str(gain)
            assert row.pop("display_tone_gain")==str(tone)
            assert row.pop("display_view")==view
        results.append(rows)
    assert results[0]==results[1]==results[2]
    assert results[0][1]["relative_direct_dose"]=="1.0"
    assert results[0][1]["changed_mas"]=="11.25"


@pytest.mark.parametrize("mas", [0,-1,150.1,float("nan"),float("inf"),True,"5"])
def test_invalid_actual_mas(mas):
    with pytest.raises(ValueError):
        calculate_exposure(compare(),mas)


@pytest.mark.parametrize("dose,tone,q", [(0,1,[0]),(float("nan"),1,[0]),(1,0,[0]),
                                         (1,True,[0]),(1,1,[1.1]),(1,1,[float("inf")])])
def test_invalid_display_inputs(dose,tone,q):
    with pytest.raises(ValueError):
        film_brightness(q,dose,tone)


APP=Path(__file__).resolve().parents[1]/"app.py"


def test_ui_manual_mas_persists_through_sid_reference_and_display_changes():
    a=AppTest.from_file(str(APP),default_timeout=20).run()
    assert not a.exception
    assert a.number_input(key="changed_mas").value==5
    a.number_input(key="changed_mas").set_value(11.25).run()
    assert not a.exception
    assert any("変更後 / 基準＝1.00000" in c.value for c in a.caption)
    geometric=[m.value for m in a.metric[2:]]
    a.number_input(key="changed_mas").set_value(8).run()
    assert [m.value for m in a.metric[2:]]==geometric
    for key,value in [("changed_sid",80),("reference_sid",120),("reference_mas",10.)]:
        a.slider(key=key).set_value(value).run()
        assert a.number_input(key="changed_mas").value==8
    numerical=[m.value for m in a.metric]
    a.selectbox(key="tone_gain").select(3).run()
    a.selectbox(key="gain").select(10).run()
    assert not a.exception
    assert [m.value for m in a.metric]==numerical
    assert a.number_input(key="changed_mas").value==8
    assert any("DR画像の表示輝度" in m.value for m in a.info)


def test_actual_mas_and_tone_are_session_local():
    a=AppTest.from_file(str(APP),default_timeout=20).run()
    b=AppTest.from_file(str(APP),default_timeout=20).run()
    a.number_input(key="changed_mas").set_value(11.25).run()
    a.selectbox(key="tone_gain").select(3).run()
    b.run()
    assert b.number_input(key="changed_mas").value==5
    assert b.selectbox(key="tone_gain").value==1
    assert not a.exception and not b.exception
