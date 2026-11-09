"""Educational film-like grayscale. NOT optical density or a measured H&D curve."""

import numpy as np

OBJECT_TRANSMISSION = 0.35  # Assumed, fixed; no material/tissue inference.
TONE_GAINS = (1, 2, 3)


def validate_tone_gain(tone_gain: int) -> None:
    if isinstance(tone_gain, bool) or tone_gain not in TONE_GAINS:
        raise ValueError("濃淡の表示係数は1・2・3から選択してください。")


def film_brightness(open_fraction, dose: float, tone_gain: int = 1) -> np.ndarray:
    """B=1/(1+a*R*T), same fixed scale for every image and pixel.

    open_fraction: fraction of the uniform focal line visible past the object.
    T=0.35+0.65*open_fraction. Both direct and attenuated signals depend on R.
    B=0 is black, B=1 is white; a is display-only, never an exposure correction.
    """
    validate_tone_gain(tone_gain)
    q = np.asarray(open_fraction, dtype=float)
    if not np.all(np.isfinite(q)) or np.any(q < 0) or np.any(q > 1):
        raise ValueError("幾何学的な開放率は0〜1の有限値が必要です。")
    if not np.isfinite(dose) or dose <= 0:
        raise ValueError("相対線量は正の有限値が必要です。")
    local_transmission = OBJECT_TRANSMISSION + (1 - OBJECT_TRANSMISSION) * q
    return 1 / (1 + tone_gain * dose * local_transmission)
