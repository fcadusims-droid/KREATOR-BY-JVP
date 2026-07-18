"""K Thumbnail — a programmatic thumbnail editor over real frames.

Works like an experienced Photoshop editor, never like a generator (spec §6):
pick the strongest real frame, crop it to composition, lift contrast and
color, sharpen, optionally set the creator's own title text — every pixel from
the footage, every effect a deterministic transform. What it never does:
fabricate a scene, an expression, or an object that was not in the video.
"""

from .pick import pick_thumbnail_times
from .compose import ThumbStyle, make_thumbnail, make_thumbnails

__all__ = ["pick_thumbnail_times", "ThumbStyle", "make_thumbnail",
           "make_thumbnails"]
