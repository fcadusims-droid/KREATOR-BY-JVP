"""K Montage — editing craft that generalizes past gameplay.

The gameplay path emphasizes hits; documentary, vlog, and travel need a
different grammar: a slow Ken Burns push over a held or scenic shot, B-roll
cutaways laid over narration (from the creator's own other footage or the K
Library), and a music bed that ducks under the voice. This module plans those
moves deterministically from the edit's own segments and transcript — the
executor already renders them (`ken_burns`, `broll`, `music.duck`).
"""

from .plan import plan_ken_burns, plan_broll

__all__ = ["plan_ken_burns", "plan_broll"]
