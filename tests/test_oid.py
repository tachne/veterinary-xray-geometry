import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

from geometry.export import comparison_rows
from geometry.model import compare, calculate_geometry
from geometry.oid import oid_comparison, oid_projection_figure, distance_figure
from geometry.render import projection_figure, geometry_figure

ROOT = Path(__file__).resolve().parents[1]
REFERENCE_CASES = json.loads((ROOT/'tests/fixtures/sid_v020_reference.json').read_text())


@pytest.mark.parametrize('case', REFERENCE_CASES, ids=[c['name'] for c in REFERENCE_CASES])
def test_sid_v020_exact_numerical_csv_and_figure_regression(case):
    c = compare(**case['inputs'])
    rows = comparison_rows(c,case['gain'],case['view'],changed_mas=case['actual_mas'],tone_gain=case['tone'])
    for row in rows:
        row.pop('app_version')  # This is the only changed CSV value.
    assert rows == case['rows']
    image = projection_figure(c,case['gain'],case['view'],changed_mas=case['actual_mas'],tone_gain=case['tone'])
    assert hashlib.sha256(image.to_json().encode()).hexdigest() == case['projection_sha256']
    assert hashlib.sha256(geometry_figure(c).to_json().encode()).hexdigest() == case['geometry_sha256']


@pytest.mark.parametrize('oid,m,u', [(0,1,0),(10,10/9,1/9),(20,1.25,.25),(40,5/3,2/3),(50,2,1)])
def test_oid_requested_values_and_distance_diagram(oid,m,u):
    pair = oid_comparison(oid)
    g = pair.changed
    assert g.sid_cm == 100 and g.focal_mm == 1 and g.object_mm == 10
    assert g.sod_cm == 100-oid
    assert g.magnification == pytest.approx(m)
    assert g.projection_mm == pytest.approx(10*m)
    assert g.ug_mm == pytest.approx(u)
    fig = distance_figure(g)
    traces = {t.name:t for t in fig.data}
    assert traces['X線焦点'].x == (0,0)
    assert traces['画像受像面'].x == (100,100)
    assert traces['被写体'].x == (100-oid,100-oid)
    assert traces['SOD'].x == (0,100-oid)
    assert traces['OID'].x == (100-oid,100)
    assert traces['SID（＝FFD）'].x == (0,100)
    assert fig.layout.xaxis.range == (-8,108)
    assert fig.layout.yaxis.range == (-19,15)
    for trace in fig.data:
        if trace.name == '半影':
            assert trace.y[1]-trace.y[0] == pytest.approx(u)
        if trace.name == '投影線':
            slope = (trace.y[1]-trace.y[0]) / g.sod_cm
            assert trace.y[2] == pytest.approx(trace.y[0]+slope*100)


def test_oid_continuous_monotonic_geometry():
    values = [oid_comparison(float(o)).changed for o in np.linspace(0,50,501)]
    assert np.all(np.diff([g.magnification for g in values]) > 0)
    assert np.all(np.diff([g.projection_mm for g in values]) > 0)
    assert np.all(np.diff([g.ug_mm for g in values]) > 0)
    assert np.all(np.diff([g.sod_cm for g in values]) < 0)
    before,after = oid_comparison(20).changed,oid_comparison(20.00001).changed
    assert 0 < after.ug_mm-before.ug_mm < 1e-6


@pytest.mark.parametrize('oid', [-.1,50.1,100,float('inf'),float('nan'),True])
def test_oid_out_of_range_rejected(oid):
    with pytest.raises(ValueError): oid_comparison(oid)


def test_distance_figure_rejects_other_sid_or_focus():
    with pytest.raises(ValueError): distance_figure(calculate_geometry(150,20,1,10))
    with pytest.raises(ValueError): distance_figure(calculate_geometry(100,20,2,10))


@pytest.mark.parametrize('oid', [0,10,20,40,50])
@pytest.mark.parametrize('gain', [1,5,10])
def test_oid_reuses_exact_v02_blur_arrays_and_fixed_plateaux(oid,gain):
    pair = oid_comparison(oid)
    fig = oid_projection_figure(oid,gain)
    base = projection_figure(pair,gain,changed_mas=5,tone_gain=1)
    assert len(fig.data) == len(base.data)
    for a,b in zip(fig.data,base.data):
        assert a.to_plotly_json().keys() == b.to_plotly_json().keys()
        np.testing.assert_array_equal(a.x,b.x)
        np.testing.assert_array_equal(a.y,b.y)
        if a.type=='heatmap': np.testing.assert_array_equal(a.z,b.z)
    heatmaps = [t for t in fig.data if t.type=='heatmap']
    for t in heatmaps:
        z = np.array(t.z)[0]
        assert z[0] == pytest.approx(.5)
        assert z[len(z)//2] == pytest.approx(1/1.35)
    assert fig.layout.xaxis.range == fig.layout.xaxis2.range
    # Inspect visible labels, not binary array encodings that can contain any text.
    labels = [a.text for a in fig.layout.annotations]
    labels += [t.name or '' for t in fig.data]
    labels += [t.hovertemplate or '' for t in fig.data]
    assert all('mAs' not in label for label in labels)
    assert all('相対線量' not in a.text for a in fig.layout.annotations)


def test_oid_zero_identical_images_and_enhancement_does_not_change_geometry():
    for gain in (1,5,10):
        fig = oid_projection_figure(0,gain)
        np.testing.assert_array_equal(fig.data[0].z,fig.data[2].z)
        g = oid_comparison(0).changed
        assert g.magnification==1 and g.ug_mm==0


def start():
    app = AppTest.from_file(str(ROOT/'app.py'),default_timeout=20).run()
    assert not app.exception
    return app


def switch(app, label):
    # AppTest has no click API for stateful tabs; real tab clicks are checked in browser QA.
    app.session_state['experiment'] = label
    app.run()
    assert not app.exception
    return app


def metrics(app):
    values = list(app.metric)
    return [dict((m.label, m.value) for m in values[i:i+4]) for i in (0,4)]


def test_oid_screen_hides_exposure_controls_and_is_independent():
    app = start()
    app.slider(key='changed_sid').set_value(80).run()
    app.slider(key='oid').set_value(60).run()
    app.slider(key='focal').set_value(2.).run()
    app.number_input(key='changed_mas').set_value(11.25).run()
    app.selectbox(key='tone_gain').select(3).run()
    saved_metrics = [m.value for m in app.metric]
    switch(app, '実験② OID変更')
    assert [s.key for s in app.slider] == ['oid_reference_distance','oid_experiment_distance']
    assert not app.number_input
    assert all('mAs' not in m.label for m in app.metric)
    assert len(app.metric) == 8
    assert metrics(app)[0]['拡大率 M'] == '1.00000'
    assert metrics(app)[1]['拡大率 M'] == '1.25000'
    assert any('実機の検出器信号が完全に一定であることを意味しません' in x.value for x in app.info)
    app.slider(key='oid_reference_distance').set_value(10.).run()
    app.slider(key='oid_experiment_distance').set_value(50.).run()
    app.selectbox(key='oid_display_gain').select(5).run()
    assert metrics(app)[0]['幾何学的不鋭 Ug'] == '0.11111 mm'
    assert metrics(app)[1]['幾何学的不鋭 Ug'] == '1.00000 mm'
    switch(app, '実験① SID（FFD）変更')
    assert app.slider(key='changed_sid').value == 80
    assert app.slider(key='oid').value == 60
    assert app.slider(key='focal').value == 2.
    assert app.number_input(key='changed_mas').value == 11.25
    assert app.selectbox(key='tone_gain').value == 3
    assert [m.value for m in app.metric] == saved_metrics
    # Changing SID-screen state must not overwrite either OID-screen setting.
    app.slider(key='oid').set_value(0).run()
    app.slider(key='changed_sid').set_value(180).run()
    app.number_input(key='changed_mas').set_value(3).run()
    switch(app, '実験② OID変更')
    assert app.slider(key='oid_reference_distance').value == 10.
    assert app.slider(key='oid_experiment_distance').value == 50.
    assert app.selectbox(key='oid_display_gain').value == 5
    assert not app.exception


def test_terminology_and_oid_values_survive_tab_changes():
    app = switch(start(), '実験② OID変更')
    app.slider(key='oid_reference_distance').set_value(10.).run()
    app.slider(key='oid_experiment_distance').set_value(40.).run()
    switch(app, '用語と距離')
    text = '\n'.join(m.value for m in app.markdown)
    for phrase in ('Source-to-Image Receptor Distance','Focus-to-Film Distance',
                   'Object-to-Image Receptor Distance','Source-to-Object Distance'):
        assert phrase in text
    assert any('SIDとFFDは同一' in m.value for m in app.info)
    assert not app.slider and not app.number_input
    switch(app, '実験② OID変更')
    assert app.slider(key='oid_reference_distance').value == 10.
    assert app.slider(key='oid_experiment_distance').value == 40.
    assert metrics(app)[1]['拡大率 M'] == '1.66667'


def test_oid_sessions_do_not_share_state():
    a,b = start(),start()
    for app in (a,b): switch(app, '実験② OID変更')
    a.slider(key='oid_reference_distance').set_value(40.).run()
    a.slider(key='oid_experiment_distance').set_value(50.).run()
    a.selectbox(key='oid_display_gain').select(10).run()
    b.run()
    assert b.slider(key='oid_reference_distance').value == 0.
    assert b.slider(key='oid_experiment_distance').value == 20.
    assert b.selectbox(key='oid_display_gain').value == 1
    assert not a.exception and not b.exception


@pytest.mark.parametrize('reference', [-.1,50.1,100,float('inf'),float('nan'),True])
def test_reference_oid_out_of_range_rejected(reference):
    with pytest.raises(ValueError): oid_comparison(20, reference_oid_cm=reference)


@pytest.mark.parametrize('oid,m,u', [(0,1,0),(10,10/9,1/9),(20,1.25,.25),(40,5/3,2/3),(50,2,1)])
def test_reference_oid_calculations_do_not_change_other_side(oid,m,u):
    c = oid_comparison(20, reference_oid_cm=oid)
    assert c.changed == oid_comparison(20).changed
    assert c.reference.magnification == pytest.approx(m)
    assert c.reference.projection_mm == pytest.approx(10*m)
    assert c.reference.ug_mm == pytest.approx(u)
    assert oid_comparison(40,reference_oid_cm=oid).reference == c.reference


@pytest.mark.parametrize('reference,changed', [(0,0),(0,50),(50,0),(10,20),(20,40),(40,10),(50,50)])
@pytest.mark.parametrize('gain', [1,5,10])
@pytest.mark.parametrize('view', ['全体','右端を拡大'])
def test_oid_pair_rendering_matches_each_geometry_and_common_tones(reference,changed,gain,view):
    c = oid_comparison(changed, reference_oid_cm=reference)
    fig = oid_projection_figure(changed,gain,view,reference_oid_cm=reference)
    base = projection_figure(c,gain,view,changed_mas=5,tone_gain=1)
    for actual,expected in zip(fig.data,base.data):
        np.testing.assert_array_equal(actual.x,expected.x)
        np.testing.assert_array_equal(actual.y,expected.y)
        if actual.type == 'heatmap': np.testing.assert_array_equal(actual.z,expected.z)
    assert fig.layout.annotations[0].text == f'基準 · OID {reference:g} cm'
    assert fig.layout.annotations[1].text == f'変更後 · OID {changed:g} cm'
    assert fig.layout.xaxis.range == fig.layout.xaxis2.range == fig.layout.xaxis3.range == fig.layout.xaxis4.range
    for trace in (fig.data[0],fig.data[2]):
        assert (trace.zmin,trace.zmax) == (0,1)
        assert np.min(trace.z) >= .5-1e-12
        assert np.max(trace.z) <= 1/1.35+1e-12
        if view == '全体':
            assert trace.z[0][0] == pytest.approx(.5)
            assert trace.z[0][len(trace.x)//2] == pytest.approx(1/1.35)
    penumbrae = [s for s in fig.layout.shapes if s.type == 'rect']
    for shape,g in zip(penumbrae,(c.reference,c.changed)):
        assert shape.x1-shape.x0 == pytest.approx(gain*g.ug_mm)
        assert (shape.x0+shape.x1)/2 == pytest.approx(g.projection_mm/2)
    if reference == changed:
        np.testing.assert_array_equal(fig.data[0].z,fig.data[2].z)


def test_oid_ui_reference_and_changed_controls_are_independent():
    app = switch(start(), '実験② OID変更')
    changed_before = metrics(app)[1]
    app.slider(key='oid_reference_distance').set_value(40.).run()
    reference_after = metrics(app)[0]
    assert metrics(app)[1] == changed_before
    assert reference_after['拡大率 M'] == '1.66667'
    app.slider(key='oid_experiment_distance').set_value(10.).run()
    assert metrics(app)[0] == reference_after
    assert metrics(app)[1]['拡大率 M'] == '1.11111'
    saved = metrics(app)
    app.selectbox(key='oid_display_gain').select(10).run()
    app.selectbox(key='oid_display_view').select('右端を拡大').run()
    assert metrics(app) == saved
    assert not app.exception
