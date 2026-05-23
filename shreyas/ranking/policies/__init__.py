"""
Ranking policy loader.

Each surface (cotraveller, destination, activity) has one policy file per
version. `load_policy(surface, version=None)` returns the right policy
module for the requested surface; version defaults to RANKING_POLICY_VERSION
from shared/config.py so swapping a policy is an env-var change, not a
code change.

V1: only "v1" lives next to each surface module. Future versions can
co-exist (cotraveller_v2.py, destination_v2.py, ...) so we can A/B by
flipping the env var.
"""

from __future__ import annotations

import importlib
from typing import Any

from shared.config import RANKING_POLICY_VERSION


_VALID_SURFACES = {"cotraveller", "destination", "activity"}


def load_policy(surface: str, version: str | None = None) -> Any:
    """Import and return the policy module for a surface.

    The resolved module path is:
        shreyas.ranking.policies.{surface}

    V1 ignores `version` (only one version exists per surface). When V2
    ships, this loader can dispatch on version to pick e.g.
    `shreyas.ranking.policies.cotraveller_v2`.
    """
    if surface not in _VALID_SURFACES:
        raise ValueError(f"Unknown ranking surface {surface!r}. Known: {sorted(_VALID_SURFACES)}")

    _ = version or RANKING_POLICY_VERSION  # reserved for V2 multi-version dispatch
    return importlib.import_module(f"shreyas.ranking.policies.{surface}")
