"""K Vision — find the people on screen, so the edit can frame them.

Gameplay is framed on the crosshair; talking content is framed on the *face*.
K Vision detects faces per sampled frame (YuNet, a 230 KB CPU model) and turns
them into the same kind of per-cut horizontal focus the motion tracker
produces — so a vlog Short crops to the speaker instead of chasing background
motion. When several faces are present the one that persists and is largest
(the subject, not a passer-by) wins; a brief miss holds the last position so
the crop never snaps to center mid-sentence.

Graceful degrade, exactly like the VLM and GameSense: if the YuNet model can't
be resolved (env var ``KREATOR_FACE_MODEL``, a vendored copy, or an OpenCV
build that bundles it) the detector reports "unavailable" and callers fall
back to motion-based focus. Nothing is fabricated: a face box is a location in
real pixels.
"""

from .faces import FaceDetector, detect_faces_available
from .track import face_focus_centers, smooth_track

__all__ = ["FaceDetector", "detect_faces_available",
           "face_focus_centers", "smooth_track"]
