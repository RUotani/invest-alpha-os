from invis_alpha_os.risk.veto_rules import VetoEngine


def test_veto_rules_hard_and_soft():
    rules = {
        "hard_veto": [{"id": "h1", "metric": "market_heat", "threshold": 0.9, "message": "hard"}],
        "soft_veto": [
            {"id": "s1", "metric": "valuation_stretch", "threshold": 0.6, "message": "soft"}
        ],
    }
    out = VetoEngine(rules=rules).evaluate({"market_heat": 0.95, "valuation_stretch": 0.7})
    assert len(out) == 2
    levels = {x.level.value for x in out}
    assert "hard_veto" in levels
    assert "soft_veto" in levels


# R6.8-E: fomo_veto評価追加
def test_fomo_veto_is_evaluated():
    """fomo_vetoセクションのルールが評価対象になること（急騰追随・高値掴み警戒ルール群）。"""
    rules = {
        "hard_veto": [{"id": "h1", "metric": "market_heat", "threshold": 0.9, "message": "hard"}],
        "soft_veto": [{"id": "s1", "metric": "valuation_stretch", "threshold": 0.6, "message": "soft"}],
        "fomo_veto": [{"id": "fomo_chase_warning", "metric": "price_spike_5d", "threshold": 0.15, "message": "FOMO"}],
    }
    out = VetoEngine(rules=rules).evaluate({"market_heat": 0.5, "valuation_stretch": 0.5, "price_spike_5d": 0.20})
    assert len(out) == 1
    assert out[0].rule_id == "fomo_chase_warning"
    assert out[0].level.value == "fomo_veto"


def test_fomo_veto_does_not_fire_below_threshold():
    """price_spike_5dが閾値未満のとき、fomo_vetoは発火しないこと。"""
    rules = {
        "fomo_veto": [{"id": "fomo_chase_warning", "metric": "price_spike_5d", "threshold": 0.15, "message": "FOMO"}],
    }
    out = VetoEngine(rules=rules).evaluate({"price_spike_5d": 0.10})
    assert len(out) == 0


def test_all_three_levels_can_fire_simultaneously():
    """hard_veto・soft_veto・fomo_vetoが同時に発火できること。"""
    rules = {
        "hard_veto": [{"id": "h1", "metric": "market_heat", "threshold": 0.9, "message": "hard"}],
        "soft_veto": [{"id": "s1", "metric": "valuation_stretch", "threshold": 0.6, "message": "soft"}],
        "fomo_veto": [{"id": "fomo_chase_warning", "metric": "price_spike_5d", "threshold": 0.15, "message": "FOMO"}],
    }
    out = VetoEngine(rules=rules).evaluate({"market_heat": 0.95, "valuation_stretch": 0.7, "price_spike_5d": 0.20})
    assert len(out) == 3
    levels = {x.level.value for x in out}
    assert "hard_veto" in levels
    assert "soft_veto" in levels
    assert "fomo_veto" in levels

