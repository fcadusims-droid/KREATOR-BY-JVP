"""Kreator — The Operating System for Human Creativity.

MVP slice under construction: the minimal path required to validate **E1**
(moment-curation quality) from the product spec.

That path, and *only* that path, is implemented here:

    Signal Layer  →  K Analyst (Evidence)  →  Planner / K Clipper  →  ranking

Everything downstream of the ranking — K Editor, K Subtitle, K Thumbnail,
K Publisher, provenance, and the incremental cache — is intentionally absent.
None of it changes whether the ranking is good, and E1 is the gate that
decides whether the rest is worth building at all.
"""

__version__ = "0.0.1"
