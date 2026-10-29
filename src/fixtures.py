"""Load the repository's synthetic fixtures.

Everything is read from local files and cached in memory. Nothing is written
back to disk. The fixtures are explicitly fictional and validated by the
pydantic models in ``src.models``.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from src.models import DemoClaim, DemoPolicy, SourceRegistry

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DEMO_POLICY_PATH = DATA_DIR / "demo_policy.json"
DEMO_CLAIM_PATH = DATA_DIR / "demo_claim.json"
DEMO_TRANSACTIONS_PATH = DATA_DIR / "demo_transactions.csv"
SOURCE_REGISTRY_PATH = DATA_DIR / "source_registry.json"


def _read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def load_policy() -> DemoPolicy:
    return DemoPolicy.model_validate(_read_json(DEMO_POLICY_PATH))


@lru_cache(maxsize=1)
def load_claim() -> DemoClaim:
    return DemoClaim.model_validate(_read_json(DEMO_CLAIM_PATH))


@lru_cache(maxsize=1)
def load_source_registry() -> SourceRegistry:
    return SourceRegistry.model_validate(_read_json(SOURCE_REGISTRY_PATH))


@lru_cache(maxsize=1)
def load_demo_transactions_bytes() -> bytes:
    """Return the synthetic CSV bytes for in-memory parsing."""
    return DEMO_TRANSACTIONS_PATH.read_bytes()
