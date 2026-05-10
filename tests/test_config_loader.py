from invis_alpha_os.config.loader import load_yaml
from invis_alpha_os.config.paths import CONFIG_DIR


def test_load_watchlist_has_required_keys():
    data = load_yaml(CONFIG_DIR / "watchlist.yaml")
    assert "jp_watchlist" in data
    assert "us_watchlist" in data
    us = data["us_watchlist"]
    assert "tier_1_core" in us
    assert "tier_2_theme_peers" in us
    assert "tier_3_optional" in us
    jp = data["jp_watchlist"]
    assert isinstance(jp, list)
    assert len(jp) >= 11
    assert isinstance(jp[0], dict)
    assert jp[0].get("ticker")

