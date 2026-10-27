"""The balance simulator runs end to end and stays deterministic for a seed."""

import random

import pytest

from engine import config
from engine.simulate import Totals, Universe, draft, main, run, simulate_campaign
from engine.squads import squad_errors


def test_popular_drafts_are_valid() -> None:
    rng = random.Random(3)
    universe = Universe.build(rng)
    zone = set(rng.sample(sorted(universe.instruments), config.CONFLICT_ZONE_SIZE))
    for commander in ("bastion", "quartermaster"):
        for _ in range(50):
            squad = draft(rng, universe, zone, commander)
            assert squad_errors(squad, commander, universe.instruments, zone) == []


@pytest.mark.parametrize("players", [3, 4, 5])
def test_campaigns_run(players: int) -> None:
    totals = Totals()
    rng = random.Random(players)
    for _ in range(3):
        simulate_campaign(rng, players, 4, totals)
    assert sum(totals.appearances.values()) == 3 * players
    assert sum(totals.wins.values()) == pytest.approx(3)
    assert totals.player_weeks == 3 * 4 * players


def test_report_is_deterministic(capsys: pytest.CaptureFixture[str]) -> None:
    assert run(3, 2, 5, seed=7) == run(3, 2, 5, seed=7)
    main(["--players", "3", "--weeks", "2", "--runs", "2"])
    out = capsys.readouterr().out
    assert "fair share=33.3%" in out and all(c in out for c in config.COMMANDERS)
