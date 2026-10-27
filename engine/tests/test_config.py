import json

from engine import config


def test_game_config_is_json_and_complete() -> None:
    json.dumps(config.GAME_CONFIG)
    assert config.GAME_CONFIG["orders"].keys() == config.ORDERS.keys()  # type: ignore[attr-defined]


def test_tables_are_consistent() -> None:
    assert set(config.SLOT_MULTIPLIERS) == set(config.FRONT_SLOTS)
    for players, points in config.CAMPAIGN_POINTS.items():
        assert len(points) == players and list(points) == sorted(points, reverse=True)
    assert min(config.CAMPAIGN_POINTS) == config.MIN_PLAYERS
    assert max(config.CAMPAIGN_POINTS) == config.MAX_PLAYERS
    for group in (
        config.ONCE_PER_WEEK_ORDERS,
        config.TARGETED_ORDERS,
        config.ORDERS_WITH_TARGET_SLOT,
        config.BERSERKER_FORBIDDEN_ORDERS,
    ):
        assert set(group) <= set(config.ORDERS)
    assert len(config.RESERVE_SLOTS) >= config.QUARTERMASTER_RESERVE_SIZE
    assert len(set(config.INVITE_CODE_ALPHABET)) == len(config.INVITE_CODE_ALPHABET)
