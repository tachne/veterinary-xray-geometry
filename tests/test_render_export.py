import csv
import io

import numpy as np
import pytest

from geometry import MODEL_VERSION
from geometry.export import csv_bytes
from geometry.model import compare
from geometry.exposure import calculate_exposure
from geometry.film_display import film_brightness
from geometry.render import common_range, geometry_figure, projection_figure, transmission


def test_exact_edge_ramp_width_not_gaussian_sigma():
    # P=12.5 mm, U=.25 mm: right edge has a linear full-width ramp.
    x=np.array([6.125,6.1875,6.25,6.3125,6.375])
    np.testing.assert_allclose(transmission(x,12.5,.25),[0,.25,.5,.75,1])


def test_profile_matches_independent_uniform_source_ray_average():
    g=compare().reference
    sources=np.linspace(-g.focal_mm/2,g.focal_mm/2,20001)
    x=np.linspace(-7,7,89)
    shifts=-(g.magnification-1)*sources
    ray_average=1-np.mean(np.abs(x[:,None]-shifts[None,:]) < g.projection_mm/2,axis=1)
    np.testing.assert_allclose(transmission(x,g.projection_mm,g.ug_mm),ray_average,atol=1e-4)


@pytest.mark.parametrize("focal,oid", [(0,20),(1,0),(0,0)])
def test_zero_penumbra_is_sharp_and_finite(focal,oid):
    g=compare(oid_cm=oid,focal_mm=focal).reference
    x=np.array([-g.projection_mm,0,g.projection_mm])
    np.testing.assert_array_equal(transmission(x,g.projection_mm,g.ug_mm),[1,0,1])


def test_edge_amplification_changes_width_only_and_handles_overlap():
    g=compare().reference
    edge=g.projection_mm/2
    for gain in (1,5,10):
        u=g.ug_mm*gain
        np.testing.assert_allclose(transmission([edge-u/2,edge,edge+u/2],g.projection_mm,u),[0,.5,1])
    # Very wide display-only blur: both edge ramps overlap, no negative fluence.
    np.testing.assert_allclose(transmission([0],35,120),[1-35/120])


@pytest.mark.parametrize("gain", [1,5,10])
@pytest.mark.parametrize("view", ["全体","右端を拡大"])
def test_comparison_uses_identical_axes_levels_and_exact_breakpoints(gain,view):
    c=compare()
    fig=projection_figure(c,gain,view)
    limits=common_range(c,gain,view)
    for axis in (fig.layout.xaxis,fig.layout.xaxis2,fig.layout.xaxis3,fig.layout.xaxis4):
        assert axis.range==limits and axis.fixedrange
    heatmaps=[t for t in fig.data if t.type=="heatmap"]
    assert len(heatmaps)==2
    np.testing.assert_array_equal(heatmaps[0].x,heatmaps[1].x)
    assert all((t.zmin,t.zmax)==(0,1) for t in heatmaps)
    profiles=[t for t in fig.data if t.name.startswith("profile_")]
    e=calculate_exposure(c)
    for trace,g,dose in zip(profiles,(c.reference,c.changed),(e.reference_relative_dose,e.changed_relative_dose)):
        for v in ((g.projection_mm-g.ug_mm*gain)/2,(g.projection_mm+g.ug_mm*gain)/2):
            assert np.any(np.isclose(trace.x,v,atol=1e-12))
        np.testing.assert_allclose(trace.y,film_brightness(transmission(trace.x,g.projection_mm,g.ug_mm*gain),dose))


def test_ray_plot_uses_actual_coordinates_and_matching_scales():
    c=compare()
    fig=geometry_figure(c)
    assert fig.layout.xaxis.range==fig.layout.xaxis2.range
    assert fig.layout.yaxis.range==fig.layout.yaxis2.range
    for i,g in enumerate((c.reference,c.changed),1):
        rays=[t for t in fig.data if t.name==f"ray_{i}"]
        assert len(rays)==4
        for ray in rays:
            assert ray.x==(0,g.sod_cm,g.sid_cm)
            assert abs(ray.y[0])==g.focal_mm/2
            assert abs(ray.y[1])==g.object_mm/2
            slope=(ray.y[1]-ray.y[0])/g.sod_cm
            assert ray.y[2]==pytest.approx(ray.y[0]+slope*g.sid_cm)
        penumbrae=[t for t in fig.data if t.name==f"penumbra_{i}"]
        assert len(penumbrae)==2
        assert all(t.y[1]-t.y[0]==pytest.approx(g.ug_mm) for t in penumbrae)


def test_csv_preserves_all_inputs_full_precision_units_and_physical_values():
    c=compare()
    datasets=[]
    for gain in (1,10):
        payload=csv_bytes(c,gain)
        assert payload.startswith(b"\xef\xbb\xbf")
        rows=list(csv.DictReader(io.StringIO(payload.decode("utf-8-sig"))))
        assert len(rows)==2
        assert rows[0]["condition"]=="reference" and rows[1]["condition"]=="changed"
        assert float(rows[1]["geometric_unsharpness_mm"])==c.changed.ug_mm
        assert float(rows[1]["sod_cm"])==130
        assert float(rows[1]["mas_correction_factor"])==2.25
        assert float(rows[1]["changed_mas"])==5
        assert float(rows[1]["theoretical_changed_mas"])==11.25
        assert rows[0]["model_version"]==MODEL_VERSION
        assert float(rows[1]["display_penumbra_gain"])==gain
        for row in rows:
            row.pop("display_penumbra_gain")
        datasets.append(rows)
    assert datasets[0]==datasets[1]


@pytest.mark.parametrize("p,u", [(0,1),(1,-1),(float("inf"),1),(1,float("nan"))])
def test_invalid_profile_rejected(p,u):
    with pytest.raises(ValueError):
        transmission([0],p,u)


@pytest.mark.parametrize("gain,view", [(0,"全体"),(2,"全体"),(True,"全体"),(1,"unknown")])
def test_invalid_display_settings_rejected(gain,view):
    with pytest.raises(ValueError):
        projection_figure(compare(),gain,view)


def test_deterministic_render_and_csv():
    assert projection_figure(compare()).to_json()==projection_figure(compare()).to_json()
    assert csv_bytes(compare())==csv_bytes(compare())
