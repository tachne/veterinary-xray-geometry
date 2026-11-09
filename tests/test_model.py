from dataclasses import FrozenInstanceError
import math

import pytest

from geometry.model import calculate_geometry, compare, corrected_mas, edge_intersections, mas_factor


@pytest.mark.parametrize("sid,oid,f,m,u", [
    pytest.param(100, 0, 1, 1, 0, id="A"),
    pytest.param(100, 20, 1, 1.25, .25, id="B"),
    pytest.param(100, 20, 2, 1.25, .50, id="C"),
    pytest.param(150, 20, 1, 15/13, 2/13, id="D"),
    pytest.param(100, 20, 0, 1.25, 0, id="E"),
])
def test_reference_geometry(sid, oid, f, m, u):
    g = calculate_geometry(sid, oid, f, 10)
    assert g.sod_cm == sid - oid
    assert g.magnification == pytest.approx(m)
    assert g.ug_mm == pytest.approx(u)
    assert g.projection_mm == pytest.approx(10*m)


@pytest.mark.parametrize("sid,oid", [(100,100), (70,80), (0,0), (-1,0)])
def test_F_invalid_geometry(sid, oid):
    with pytest.raises(ValueError):
        calculate_geometry(sid, oid, 1, 10)


@pytest.mark.parametrize("sid,factor", [(150,2.25), (80,.64), (100,1), (180,3.24)], ids=list("GHIJ"))
def test_mas_reference_cases(sid, factor):
    assert mas_factor(100, sid) == pytest.approx(factor)


def test_K_other_inputs_leave_factor_unchanged():
    for oid in (0,20,60):
        for focal in (0,1,2):
            for dimension in (5,10,30):
                for mas in (1,5,20):
                    c = compare(100,150,oid,focal,dimension,mas)
                    assert c.correction_factor == 2.25
                    assert c.changed_mas == mas * 2.25


def test_L_initial_mas():
    assert corrected_mas(100,150,5) == 11.25


@pytest.mark.parametrize("index,value", [(0,69), (0,181), (1,-1), (1,61), (2,-.1), (2,2.1),
                                         (3,4), (3,31), (0,float("inf")), (1,float("nan")),
                                         (2,True), (3,"10")])
def test_input_bounds(index, value):
    args=[100,20,1,10]
    args[index]=value
    with pytest.raises(ValueError):
        calculate_geometry(*args)


@pytest.mark.parametrize("args", [(0,150,5),(100,0,5),(100,150,0),(100,150,21),
                                  (100,150,float("nan")),(float("inf"),150,5)])
def test_mas_invalid_values(args):
    with pytest.raises(ValueError):
        corrected_mas(*args)


def test_all_boundary_combinations_and_inverse_square_identity():
    for sid1 in (70,100,180):
        for sid2 in (70,100,180):
            for oid in (0,60):
                for focal in (0,2):
                    for dimension in (5,30):
                        c=compare(sid1,sid2,oid,focal,dimension,20)
                        assert c.changed_mas/sid2**2 == pytest.approx(20/sid1**2)
                        for g in (c.reference,c.changed):
                            assert g.sod_cm>0 and g.magnification>=1
                            assert all(math.isfinite(v) for v in vars(g).values())
                            assert g.ug_mm == pytest.approx(g.focal_mm*(g.magnification-1))
                            for intersections in edge_intersections(g):
                                assert abs(intersections[1]-intersections[0]) == pytest.approx(g.ug_mm)
    assert corrected_mas(70,180,20)>20  # No clipping to the input range.


def test_results_are_immutable():
    with pytest.raises(FrozenInstanceError):
        compare().reference.sid_cm=140
