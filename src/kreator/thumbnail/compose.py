"""Compose a thumbnail from a real frame — crop, enhance, optional title.

All OpenCV, all deterministic, all on pixels that existed in the footage. The
enhancement is the standard thumbnail treatment a human editor applies: a
contrast/brightness lift, a saturation push, an unsharp mask. Text (when the
creator provides it) is drawn with a heavy outline so it reads at feed size.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ..reframe import crop_window


@dataclass(frozen=True)
class ThumbStyle:
    """The treatment. Part of the channel's Editing Profile eventually."""
    width: int = 1280
    height: int = 720
    contrast: float = 1.15      # alpha in convertScaleAbs
    brightness: int = 8         # beta
    saturation: float = 1.25
    sharpen: float = 0.5        # unsharp-mask amount; 0 disables
    text_scale: float = 2.2
    text_thickness: int = 5

    def to_dict(self) -> dict:
        return {"width": self.width, "height": self.height,
                "contrast": self.contrast, "brightness": self.brightness,
                "saturation": self.saturation, "sharpen": self.sharpen}


def enhance_frame(frame, style: ThumbStyle):
    """The deterministic treatment: contrast → saturation → unsharp mask.
    Takes and returns a BGR ndarray; transforms pixels, never invents them."""
    import cv2
    import numpy as np

    out = cv2.convertScaleAbs(frame, alpha=style.contrast, beta=style.brightness)
    if style.saturation != 1.0:
        hsv = cv2.cvtColor(out, cv2.COLOR_BGR2HSV).astype(np.float32)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * style.saturation, 0, 255)
        out = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
    if style.sharpen > 0:
        blur = cv2.GaussianBlur(out, (0, 0), 3)
        out = cv2.addWeighted(out, 1.0 + style.sharpen, blur, -style.sharpen, 0)
    return out


def _draw_title(img, text: str, style: ThumbStyle):
    """The creator's own title, bottom-left, white over a heavy black outline."""
    import cv2

    x = int(img.shape[1] * 0.045)
    y = int(img.shape[0] * 0.92)
    for color, thickness in (((0, 0, 0), style.text_thickness * 3),
                             ((255, 255, 255), style.text_thickness)):
        cv2.putText(img, text, (x, y), cv2.FONT_HERSHEY_DUPLEX,
                    style.text_scale, color, thickness, cv2.LINE_AA)
    return img


def make_thumbnail(
    video_path: str,
    t: float,
    out_path: str,
    *,
    focus_x: float = 0.5,
    text: str | None = None,
    style: ThumbStyle | None = None,
) -> dict:
    """One real frame at ``t`` → a treated 16:9 thumbnail JPEG."""
    import cv2

    style = style or ThumbStyle()
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"cannot open video: {video_path}")
    cap.set(cv2.CAP_PROP_POS_MSEC, max(0.0, t) * 1000.0)
    ok, frame = cap.read()
    cap.release()
    if not ok:
        raise RuntimeError(f"cannot read a frame at {t:.2f}s")

    h, w = frame.shape[:2]
    x, y, cw, ch = crop_window(w, h, f"{style.width}:{style.height}", focus_x)
    frame = frame[y:y + ch, x:x + cw]
    frame = cv2.resize(frame, (style.width, style.height),
                       interpolation=cv2.INTER_AREA)
    frame = enhance_frame(frame, style)
    if text:
        frame = _draw_title(frame, text, style)

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(out_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return {"file": Path(out_path).name, "time": round(t, 2),
            "text": text or "", "style": style.to_dict()}


def make_thumbnails(
    video_path: str,
    bundle,
    out_dir: str,
    *,
    n: int = 3,
    text: str | None = None,
    style: ThumbStyle | None = None,
) -> list[dict]:
    """The top-``n`` moments → treated thumbnail candidates + a manifest."""
    from .pick import pick_thumbnail_times

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    entries = []
    for i, t in enumerate(pick_thumbnail_times(bundle, n), start=1):
        entries.append(make_thumbnail(
            video_path, t, str(out / f"thumb_{i:02d}.jpg"),
            text=text, style=style))
    (out / "thumbnails.json").write_text(json.dumps(entries, indent=2),
                                         encoding="utf-8")
    return entries
