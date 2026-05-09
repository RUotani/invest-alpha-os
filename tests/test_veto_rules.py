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

