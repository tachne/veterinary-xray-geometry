"""Two deterministic rows, generated in memory; no server-side student records."""

import csv
import io

from . import APP_VERSION, MODEL_VERSION, EXPOSURE_MODEL_VERSION, DISPLAY_MODEL_VERSION
from .exposure import calculate_exposure, DOSE_UNIT_SID_CM, DOSE_UNIT_MAS
from .film_display import OBJECT_TRANSMISSION, validate_tone_gain
from .model import Comparison
from .render import display_settings


def comparison_rows(c: Comparison, gain=1, view="全体", *, changed_mas=5.0, tone_gain=1) -> list[dict]:
    display_settings(gain, view)
    validate_tone_gain(tone_gain)
    exposure = calculate_exposure(c, changed_mas)
    rows = []
    for role, g, mas, dose in [("reference", c.reference, c.reference_mas, exposure.reference_relative_dose),
                               ("changed", c.changed, changed_mas, exposure.changed_relative_dose)]:
        rows.append(dict(condition=role, reference_sid_cm=c.reference.sid_cm,
                         changed_sid_cm=c.changed.sid_cm, sid_cm=g.sid_cm,
                         oid_cm=g.oid_cm, sod_cm=g.sod_cm, focal_size_mm=g.focal_mm,
                         object_size_mm=g.object_mm, magnification=g.magnification,
                         projection_mm=g.projection_mm, geometric_unsharpness_mm=g.ug_mm,
                         reference_mas=c.reference_mas, mas_correction_factor=c.correction_factor,
                         changed_mas=changed_mas, theoretical_changed_mas=c.changed_mas, condition_mas=mas,
                         relative_direct_dose=dose, changed_to_reference_dose_ratio=exposure.changed_to_reference_ratio,
                         dose_unit_sid_cm=DOSE_UNIT_SID_CM, dose_unit_mas=DOSE_UNIT_MAS,
                         object_transmission_assumed=OBJECT_TRANSMISSION,
                         display_penumbra_gain=gain, display_view=view,
                         display_tone_gain=tone_gain,
                         model_version=MODEL_VERSION, exposure_model_version=EXPOSURE_MODEL_VERSION,
                         display_model_version=DISPLAY_MODEL_VERSION, app_version=APP_VERSION))
    return rows


def csv_bytes(c: Comparison, gain=1, view="全体", *, changed_mas=5.0, tone_gain=1) -> bytes:
    rows = comparison_rows(c, gain, view, changed_mas=changed_mas, tone_gain=tone_gain)
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8-sig")
