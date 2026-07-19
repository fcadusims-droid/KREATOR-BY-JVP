"""K Polish — universal visual correction for real-world footage.

Gameplay ships with correct, stylized colors; a phone-shot vlog or a
documentary clip often does not — a colour cast, under- or over-exposure. K
Polish measures a handful of frames and computes a gray-world white balance
plus an exposure lift, expressed as a ColorFix the executor applies to real
pixels (it corrects toward neutral, invents nothing). Off for gameplay, where
the look is intentional.
"""

from .correct import gray_world_fix, measure_color

__all__ = ["measure_color", "gray_world_fix"]
