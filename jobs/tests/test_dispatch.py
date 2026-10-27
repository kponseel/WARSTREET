"""Front Dispatch: no leak of hidden players, EN/FR rendering, variant parity."""

from __future__ import annotations

import re

import pytest

from jobs import dispatch
from jobs.dispatch import LivePlayer

EDITIONS = ("monday", "monday_fog", "thursday", "debrief")


def test_hidden_players_never_lead() -> None:
    players = [
        LivePlayer("Shade", None, True),
        LivePlayer("Jammed", None, True),
        LivePlayer("Ava", 12.0, False),
        LivePlayer("Bob", 30.0, False),
    ]
    d = dispatch.monday("L", "2026-11-09", players, "NVDA", 4.26)
    assert d.template_key == "dispatch.monday"
    assert d.vars["leader"] == "Bob" and d.vars["pf"] == 30 and d.vars["move"] == 4.3
    for language in ("en", "fr"):
        text = dispatch.render(d, language)
        assert "Shade" not in text and "Jammed" not in text and "Bob" in text


def test_fog_when_nobody_is_visible() -> None:
    d = dispatch.monday("L", "2026-11-09", [LivePlayer("Shade", None, True)], None, None)
    assert d.template_key == "dispatch.monday_fog"
    assert "leader" not in d.vars and d.vars["mover"] == "-"


def test_variant_is_deterministic_and_in_range() -> None:
    a = dispatch.pick_variant("L", "2026-11-09", "monday")
    assert a == dispatch.pick_variant("L", "2026-11-09", "monday")
    seen = {dispatch.pick_variant(f"L{i}", "2026-11-09", "debrief") for i in range(60)}
    assert seen == set(range(dispatch.VARIANTS))


@pytest.mark.parametrize("edition", EDITIONS)
def test_every_variant_exists_in_both_languages_with_the_same_variables(edition: str) -> None:
    en, fr = dispatch.messages("en"), dispatch.messages("fr")
    for variant in range(dispatch.VARIANTS):
        key = f"dispatch.{edition}.{variant}"
        assert key in en and key in fr
        assert set(re.findall(r"\{(\w+)\}", en[key])) == set(re.findall(r"\{(\w+)\}", fr[key]))


def test_thursday_and_debrief_render_every_variable() -> None:
    editions = [
        dispatch.thursday("L", "w", swaps=3, attacks=2, blocked=1, pacts=1),
        dispatch.debrief(
            "L",
            "w",
            winner="Ava",
            pf=41,
            best="NVDA",
            best_move=8.2,
            worst="KO",
            worst_move=-3.1,
            drone_pf=12,
            rusty=1,
        ),
    ]
    for d in editions:
        for language in ("en", "fr"):
            text = dispatch.render(d, language)
            assert "{" not in text and text.strip()
