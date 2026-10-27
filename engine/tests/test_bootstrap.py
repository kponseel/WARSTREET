import importlib
import re
from pathlib import Path

import pytest

from engine.config import GAME_NAME

REPO_ROOT = Path(__file__).resolve().parents[2]

MODULES = [
    "calendar",
    "commanders",
    "config",
    "conflict_zone",
    "drone",
    "feats",
    "models",
    "orders",
    "ranking",
    "scoring",
    "simulate",
    "weather",
]


def test_game_name() -> None:
    assert GAME_NAME == "WARSTREET"


def test_game_name_matches_web_config() -> None:
    web_config = (REPO_ROOT / "web" / "src" / "config.ts").read_text(encoding="utf-8")
    match = re.search(r"export const GAME_NAME = '([^']+)'", web_config)
    assert match is not None, "GAME_NAME not found in web/src/config.ts"
    assert match.group(1) == GAME_NAME


@pytest.mark.parametrize("name", MODULES)
def test_module_imports(name: str) -> None:
    module = importlib.import_module(f"engine.{name}")
    assert module.__doc__
