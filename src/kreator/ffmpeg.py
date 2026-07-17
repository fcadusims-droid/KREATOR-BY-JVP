"""One place to resolve the FFmpeg binary — every module imports from here.

Prefers a system ffmpeg on PATH; falls back to the binary bundled with
imageio-ffmpeg when installed. Returning the bare name as a last resort lets
subprocess raise a clear "not found" instead of us guessing.
"""

from __future__ import annotations

import shutil


def ffmpeg_bin() -> str:
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg  # type: ignore

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # pragma: no cover
        return "ffmpeg"
