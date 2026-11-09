"""Pure calculations. Distances: cm; transverse dimensions: mm; exposure: mAs."""

from dataclasses import dataclass
from math import isfinite


def bounded(name: str, value: float, low: float, high: float) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name}: 数値を入力してください。")
    if not isfinite(value) or not low <= value <= high:
        raise ValueError(f"{name}: {low:g}〜{high:g}の有限値を入力してください。")


@dataclass(frozen=True)
class Geometry:
    sid_cm: float
    oid_cm: float
    focal_mm: float
    object_mm: float
    sod_cm: float
    magnification: float
    projection_mm: float
    ug_mm: float


def calculate_geometry(sid_cm: float, oid_cm: float, focal_mm: float,
                       object_mm: float) -> Geometry:
    bounded("SID (cm)", sid_cm, 70, 180)
    bounded("OID (cm)", oid_cm, 0, 60)
    if sid_cm <= oid_cm:
        raise ValueError("SID > OID が必要です。")
    bounded("実効焦点サイズ (mm)", focal_mm, 0, 2)
    bounded("被写体実寸法 (mm)", object_mm, 5, 30)
    sod_cm = sid_cm - oid_cm
    magnification = sid_cm / sod_cm
    return Geometry(sid_cm, oid_cm, focal_mm, object_mm, sod_cm,
                    magnification, object_mm * magnification,
                    focal_mm * oid_cm / sod_cm)


def mas_factor(reference_sid_cm: float, changed_sid_cm: float) -> float:
    """Inverse square correction only. No object or focal-spot arguments."""
    bounded("基準SID (cm)", reference_sid_cm, 70, 180)
    bounded("変更後SID (cm)", changed_sid_cm, 70, 180)
    return (changed_sid_cm / reference_sid_cm) ** 2


def corrected_mas(reference_sid_cm: float, changed_sid_cm: float,
                  reference_mas: float) -> float:
    bounded("基準mAs", reference_mas, 1, 20)
    return reference_mas * mas_factor(reference_sid_cm, changed_sid_cm)


@dataclass(frozen=True)
class Comparison:
    reference: Geometry
    changed: Geometry
    reference_mas: float
    correction_factor: float
    changed_mas: float


def compare(reference_sid_cm=100.0, changed_sid_cm=150.0, oid_cm=20.0,
            focal_mm=1.0, object_mm=10.0, reference_mas=5.0) -> Comparison:
    reference = calculate_geometry(reference_sid_cm, oid_cm, focal_mm, object_mm)
    changed = calculate_geometry(changed_sid_cm, oid_cm, focal_mm, object_mm)
    return Comparison(reference, changed, reference_mas,
                      mas_factor(reference_sid_cm, changed_sid_cm),
                      corrected_mas(reference_sid_cm, changed_sid_cm, reference_mas))


def ray_endpoint(g: Geometry, source_mm: float, object_edge_mm: float) -> float:
    """Transverse detector coordinate of a ray, derived from similar triangles."""
    return source_mm + (object_edge_mm - source_mm) * g.sid_cm / g.sod_cm


def edge_intersections(g: Geometry) -> tuple[tuple[float, float], ...]:
    """Two ray intersections per object edge; each separation is detector Ug."""
    return tuple(tuple(ray_endpoint(g, source, edge)
                       for source in (-g.focal_mm / 2, g.focal_mm / 2))
                 for edge in (-g.object_mm / 2, g.object_mm / 2))
