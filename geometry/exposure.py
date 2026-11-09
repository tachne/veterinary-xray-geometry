"""Relative direct-field detector exposure. Independent of image display settings."""

from dataclasses import dataclass

from .model import Comparison, bounded

DOSE_UNIT_SID_CM = 100.0
DOSE_UNIT_MAS = 5.0
CHANGED_MAS_MIN = 0.1
CHANGED_MAS_MAX = 150.0


def relative_dose(sid_cm: float, mas: float) -> float:
    """Direct field: the fixed 100 cm / 5 mAs condition is 1 (not patient dose)."""
    bounded("SID (cm)", sid_cm, 70, 180)
    bounded("mAs", mas, CHANGED_MAS_MIN, CHANGED_MAS_MAX)
    return (mas / DOSE_UNIT_MAS) * (DOSE_UNIT_SID_CM / sid_cm) ** 2


@dataclass(frozen=True)
class Exposure:
    reference_relative_dose: float
    changed_relative_dose: float
    changed_to_reference_ratio: float
    changed_mas: float


def calculate_exposure(c: Comparison, changed_mas: float = 5.0) -> Exposure:
    """The supplied mAs is never replaced by c.changed_mas (the theoretical value)."""
    reference = relative_dose(c.reference.sid_cm, c.reference_mas)
    changed = relative_dose(c.changed.sid_cm, changed_mas)
    return Exposure(reference, changed, changed / reference, changed_mas)
