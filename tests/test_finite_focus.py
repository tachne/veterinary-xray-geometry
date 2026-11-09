import copy
import json
from pathlib import Path

import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

from geometry.finite_focus import shadow_edges, finite_focus_figure, current_comparisons
from geometry.model import compare
from geometry.oid import oid_comparison
from geometry.render import transmission
from geometry.export import csv_bytes

APP = Path(__file__).resolve().parents[1]/'app.py'


@pytest.mark.parametrize('focal', [0,.1,1,2])
@pytest.mark.parametrize('oid', [0,20,60])
def test_four_rays_and_shadow_regions_match_physical_formula(focal,oid):
    pair = compare(100,150,oid,focal,10)
    fig = finite_focus_figure(pair)
    assert fig.layout.xaxis.range == fig.layout.xaxis2.range
    assert fig.layout.yaxis.range == fig.layout.yaxis2.range
    assert fig.layout.xaxis3.range == fig.layout.xaxis4.range
    assert fig.layout.yaxis.range[0] > fig.layout.yaxis.range[1]  # beam goes down
    for col,g in enumerate((pair.reference,pair.changed),1):
        s=shadow_edges(g)
        expected_u = focal*oid/(g.sid_cm-oid)
        assert s.left_inner-s.left_outer == pytest.approx(expected_u)
        assert s.right_outer-s.right_inner == pytest.approx(expected_u)
        assert s.right_inner-s.left_inner == pytest.approx(g.projection_mm-expected_u)
        assert s.right_outer-s.left_outer == pytest.approx(g.projection_mm+expected_u)
        rays=[t for t in fig.data if t.name==f'ray_{col}']
        assert len(rays)==4
        for r in rays:
            assert r.y == (0,g.sod_cm,g.sid_cm)
            assert abs(r.x[0]) == focal/2 and abs(r.x[1]) == g.object_mm/2
            assert r.x[2] == pytest.approx(r.x[0]+(r.x[1]-r.x[0])*g.sid_cm/g.sod_cm)
        beam=next(t for t in fig.data if t.name==f'beam_{col}')
        assert beam.x[1]-beam.x[0] == focal
        assert beam.x[2]-beam.x[3] > focal
        assert beam.y == (0,0,g.sid_cm,g.sid_cm)
        focus=next(t for t in fig.data if t.name==f'focus_{col}')
        if focal == 0:
            assert focus.mode=='markers' and focus.x==(0,)
        else:
            assert focus.mode=='lines' and focus.x==(-focal/2,focal/2)
        if expected_u == 0:
            assert not any('penumbra' in t.name and t.name.endswith(f'_{col}') for t in fig.data)
        else:
            for side,edge in (('left',-g.object_mm/2),('right',g.object_mm/2)):
                triangle=next(t for t in fig.data if t.name==f'{side}_penumbra_{col}')
                assert triangle.x[0]==edge and triangle.y==(g.sod_cm,g.sid_cm,g.sid_cm)
                assert abs(triangle.x[2]-triangle.x[1])==pytest.approx(expected_u)
        if oid > 0:
            umbra=next(t for t in fig.data if t.name==f'umbra_{col}')
            assert umbra.x == (-g.object_mm/2,g.object_mm/2,s.right_inner,s.left_inner)
    assert fig.layout.meta['penumbra_gain']==1


@pytest.mark.parametrize('dimension', [5,30])
def test_boundary_conditions_fit_scene_and_have_nonnegative_umbra(dimension):
    pair=compare(70,180,60,2,dimension)
    fig=finite_focus_figure(pair)
    for g in (pair.reference,pair.changed):
        s=shadow_edges(g)
        assert s.left_outer <= s.left_inner < s.right_inner <= s.right_outer
        assert fig.layout.xaxis.range[0] < s.left_outer < s.right_outer < fig.layout.xaxis.range[1]
        assert g.sid_cm <= fig.layout.yaxis.range[0]


@pytest.mark.parametrize('oid', [0,10,20,40,50])
def test_shadow_classification_agrees_with_existing_uniform_source_image(oid):
    g=oid_comparison(oid).changed
    s=shadow_edges(g)
    # Full shadow, partial shadow and unblocked regions use the same boundaries
    # as the existing image model, before the separate 35% transmission mapping.
    assert transmission([0],g.projection_mm,g.ug_mm)[0] == 0
    assert transmission([s.right_outer+1],g.projection_mm,g.ug_mm)[0] == 1
    if g.ug_mm:
        samples=[(s.left_inner+s.left_outer)/2,(s.right_inner+s.right_outer)/2]
        np.testing.assert_allclose(transmission(samples,g.projection_mm,g.ug_mm),[.5,.5])
    fig=finite_focus_figure(oid_comparison(oid),'oid')
    for i in (1,2):
        plane=next(t for t in fig.data if t.name==f'detector_{i}')
        assert plane.y==(100,100)
    assert fig.layout.xaxis.range == pytest.approx((-22.4,22.4))


def test_saved_conditions_read_only_and_diagram_independent_of_mas():
    state={'reference_sid':100,'changed_sid':180,'oid':60,'focal':2.,
           'reference_mas':5.,'changed_mas':11.25,'gain':10,'tone_gain':3,
           'oid_reference_distance':10.,'oid_experiment_distance':50.}
    original=copy.deepcopy(state)
    pairs=current_comparisons(state)
    assert state==original
    assert pairs[0].reference.focal_mm==2 and pairs[1].reference.focal_mm==1
    before=finite_focus_figure(pairs[0]).to_json()
    state.update(reference_mas=20.,changed_mas=150.,gain=1,tone_gain=1)
    assert finite_focus_figure(current_comparisons(state)[0]).to_json()==before
    assert current_comparisons({})[0]==compare()


def start():
    app=AppTest.from_file(str(APP),default_timeout=20).run()
    assert not app.exception
    return app


def switch(app,label):
    app.session_state['experiment']=label
    app.run()
    assert not app.exception


def focus_charts(app):
    result={}
    for chart in app.get('plotly_chart'):
        data=json.loads(chart.proto.spec)
        meta=data['layout'].get('meta',{})
        if 'penumbra_gain' in meta:
            result[meta['experiment']]=data
    return result


def test_same_diagram_used_in_experiments_and_terminology_with_no_new_controls():
    app=start()
    app.slider(key='focal').set_value(2.).run()
    app.slider(key='changed_sid').set_value(180).run()
    app.number_input(key='changed_mas').set_value(11.25).run()
    sid_chart=focus_charts(app)['sid']
    sid_metrics=[m.value for m in app.metric]
    sid_image=app.get('plotly_chart')[0].proto.spec
    before_csv=csv_bytes(current_comparisons(app.session_state)[0],changed_mas=11.25)
    switch(app,'実験② OID変更')
    app.slider(key='oid_reference_distance').set_value(10.).run()
    app.slider(key='oid_experiment_distance').set_value(50.).run()
    oid_chart=focus_charts(app)['oid']
    oid_image=app.get('plotly_chart')[0].proto.spec
    oid_metrics=[m.value for m in app.metric]
    switch(app,'用語と距離')
    assert not app.slider and not app.number_input and not app.selectbox
    assert focus_charts(app)=={'sid':sid_chart,'oid':oid_chart}
    switch(app,'実験① SID（FFD）変更')
    assert [m.value for m in app.metric]==sid_metrics
    assert app.get('plotly_chart')[0].proto.spec==sid_image
    assert csv_bytes(current_comparisons(app.session_state)[0],changed_mas=11.25)==before_csv
    switch(app,'実験② OID変更')
    assert [m.value for m in app.metric]==oid_metrics
    assert app.get('plotly_chart')[0].proto.spec==oid_image


def test_ui_focus_zero_and_image_emphasis_do_not_create_geometric_penumbra():
    app=start()
    app.slider(key='focal').set_value(0.).run()
    before=focus_charts(app)['sid']
    assert before['layout']['meta']['reference']['ug_mm']==0
    assert not any('penumbra' in t['name'] for t in before['data'])
    app.selectbox(key='gain').select(10).run()
    app.selectbox(key='tone_gain').select(3).run()
    assert focus_charts(app)['sid']==before
    switch(app,'用語と距離')
    assert focus_charts(app)['sid']==before


def test_new_diagram_session_isolation():
    a,b=start(),start()
    a.slider(key='focal').set_value(2.).run()
    switch(a,'用語と距離');switch(b,'用語と距離')
    assert focus_charts(a)['sid']['layout']['meta']['reference']['focal_mm']==2
    assert focus_charts(b)['sid']['layout']['meta']['reference']['focal_mm']==1
