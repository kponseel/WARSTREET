"""Checks that need no database: generated seed, error code translations."""

import importlib.util
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = sorted((REPO_ROOT / "supabase" / "migrations").glob("*.sql"))


def _load_generator():  # type: ignore[no-untyped-def]
    path = REPO_ROOT / "supabase" / "scripts" / "generate_seed.py"
    spec = importlib.util.spec_from_file_location("generate_seed", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_seed_matches_engine_config_and_catalogue() -> None:
    seed = (REPO_ROOT / "supabase" / "seed.sql").read_text(encoding="utf-8")
    assert seed == _load_generator().render_seed(), (
        "supabase/seed.sql is stale: run python supabase/scripts/generate_seed.py"
    )


def _error_codes() -> dict[str, set[str]]:
    """Every code raised in SQL, with the variable names it sends."""
    codes: dict[str, set[str]] = {}
    for migration in MIGRATIONS:
        text = migration.read_text(encoding="utf-8")
        for match in re.finditer(r"raise_error\('([A-Z_]+)'(.*?)\);", text, re.DOTALL):
            names = set(re.findall(r"'([a-z_]+)',", match.group(2)))
            codes.setdefault(match.group(1), set()).update(names)
    return codes


def _messages(language: str) -> dict[str, str]:
    text = (REPO_ROOT / "web" / "src" / "i18n" / f"{language}.ts").read_text(encoding="utf-8")
    pairs = re.findall(r"'(error\.[A-Za-z_]+)':\s*(['\"])(.*?)\2,", text, re.DOTALL)
    return {key: message for key, _, message in pairs}


def test_every_error_code_is_translated_with_its_variables() -> None:
    codes = _error_codes()
    assert len(codes) > 40
    for language in ("en", "fr"):
        messages = _messages(language)
        for code, names in codes.items():
            key = f"error.{code}"
            assert key in messages, f"{key} missing in web/src/i18n/{language}.ts"
            placeholders = set(re.findall(r"\{(\w+)\}", messages[key]))
            assert placeholders <= names, f"{language} {key} uses {placeholders - names}"
