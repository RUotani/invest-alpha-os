from types import SimpleNamespace

from invis_alpha_os.config import CONFIG_DIR, load_yaml
from invis_alpha_os.risk import (
    VetoEngine,
    build_momentum_veto_result,
    format_veto_table_cell,
    momentum_breakdown_veto_context,
    veto_hits_to_result_dict,
)
from invis_alpha_os.risk.veto_rules import VetoEngine as VetoEngineFromModule


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


def test_risk_package_exports_public_api() -> None:
    """risk パッケージから Veto 公開 API を import できること。"""
    assert VetoEngine is VetoEngineFromModule
    assert callable(format_veto_table_cell)
    assert callable(veto_hits_to_result_dict)
    assert callable(build_momentum_veto_result)
    assert callable(momentum_breakdown_veto_context)


def _production_veto_engine() -> VetoEngine:
    return VetoEngine(rules=load_yaml(CONFIG_DIR / "veto_rules.yaml"))


def test_production_yaml_has_no_fomo_chase_warning_rule() -> None:
    rules = load_yaml(CONFIG_DIR / "veto_rules.yaml")
    fomo_ids = [r["id"] for r in rules.get("fomo_veto", [])]
    assert "fomo_chase_warning" not in fomo_ids
    assert "fomo_volume_price_chase" in fomo_ids


def test_production_fomo_not_on_crash_r5() -> None:
    """急落（r5 < -15%）では fomo_volume_price_chase が出ないこと（6501 型の誤発火防止）。"""
    m = SimpleNamespace(r5=-0.158, volume_ratio_25d=1.56, overheat_flag=False)
    vr = build_momentum_veto_result(m, _production_veto_engine())
    rule_ids = [r["rule_id"] for r in vr.get("rules", [])]
    assert "fomo_chase_warning" not in rule_ids
    assert "fomo_volume_price_chase" not in rule_ids


def test_production_fomo_not_on_high_r5_low_volume() -> None:
    """r5 > 15% でも volume_ratio_25d < 3.0 なら fomo_volume_price_chase は出ないこと。"""
    m = SimpleNamespace(r5=0.207, volume_ratio_25d=0.51, overheat_flag=True)
    vr = build_momentum_veto_result(m, _production_veto_engine())
    rule_ids = [r["rule_id"] for r in vr.get("rules", [])]
    assert "fomo_volume_price_chase" not in rule_ids
    assert "hard_momentum_overheat" in rule_ids


def test_production_fomo_volume_price_chase_fires() -> None:
    """r5 > 15% かつ volume_ratio_25d >= 3.0 で fomo_volume_price_chase が出ること。"""
    m = SimpleNamespace(r5=0.20, volume_ratio_25d=3.5, overheat_flag=False)
    vr = build_momentum_veto_result(m, _production_veto_engine())
    rule_ids = [r["rule_id"] for r in vr.get("rules", [])]
    assert "fomo_volume_price_chase" in rule_ids


def test_all_three_levels_can_fire_simultaneously():
    """hard_veto・soft_veto・fomo_vetoが同時に発火できること。"""
    rules = {
        "hard_veto": [{"id": "h1", "metric": "market_heat", "threshold": 0.9, "message": "hard"}],
        "soft_veto": [{"id": "s1", "metric": "valuation_stretch", "threshold": 0.6, "message": "soft"}],
        "fomo_veto": [
            {
                "id": "fomo_volume_price_chase",
                "metric": "fomo_volume_price_chase",
                "threshold": 1.0,
                "message": "chase",
            }
        ],
    }
    out = VetoEngine(rules=rules).evaluate(
        {
            "market_heat": 0.95,
            "valuation_stretch": 0.7,
            "fomo_volume_price_chase": 1.0,
        }
    )
    assert len(out) == 3
    levels = {x.level.value for x in out}
    assert "hard_veto" in levels
    assert "soft_veto" in levels
    assert "fomo_veto" in levels


def test_momentum_breakdown_veto_context_volume_price_chase() -> None:
    """25日平均比の出来高倍率が閾値以上かつ r5>0.15 のときだけ合成指標が 1.0 になること。"""
    from types import SimpleNamespace

    from invis_alpha_os.risk.veto_rules import momentum_breakdown_veto_context

    hot = SimpleNamespace(r5=0.20, volume_ratio_25d=3.5, overheat_flag=False)
    assert momentum_breakdown_veto_context(hot)["fomo_volume_price_chase"] == 1.0
    cold_ratio = SimpleNamespace(r5=0.20, volume_ratio_25d=2.9, overheat_flag=False)
    assert momentum_breakdown_veto_context(cold_ratio)["fomo_volume_price_chase"] == 0.0
    cold_r5 = SimpleNamespace(r5=0.10, volume_ratio_25d=5.0, overheat_flag=False)
    assert momentum_breakdown_veto_context(cold_r5)["fomo_volume_price_chase"] == 0.0
    neg_r5 = SimpleNamespace(r5=-0.20, volume_ratio_25d=5.0, overheat_flag=False)
    assert momentum_breakdown_veto_context(neg_r5)["fomo_volume_price_chase"] == 0.0
    none_vr = SimpleNamespace(r5=0.20, volume_ratio_25d=None, overheat_flag=False)
    assert momentum_breakdown_veto_context(none_vr)["fomo_volume_price_chase"] == 0.0


def test_fomo_volume_price_chase_yaml_rule_fires() -> None:
    """config 相当の fomo_volume_price_chase ルールが合成指標で発火すること。"""
    rules = {
        "fomo_veto": [
            {
                "id": "fomo_volume_price_chase",
                "metric": "fomo_volume_price_chase",
                "threshold": 1.0,
                "message": "Volume vs 25d prior avg >= 3.0 with r5 > 15% (chase caution)",
            }
        ]
    }
    out = VetoEngine(rules=rules).evaluate({"fomo_volume_price_chase": 1.0, "price_spike_5d": 0.0})
    assert len(out) == 1
    assert out[0].rule_id == "fomo_volume_price_chase"


def test_format_veto_table_cell_dash_when_not_triggered() -> None:
    assert format_veto_table_cell({}) == "—"
    assert format_veto_table_cell({"triggered": False, "rules": []}) == "—"
    assert format_veto_table_cell({"triggered": True, "rules": []}) == "—"


def test_format_veto_table_cell_lists_rule_ids() -> None:
    vr = {"triggered": True, "rules": [{"rule_id": "a"}, {"rule_id": "b"}]}
    assert format_veto_table_cell(vr) == "⚠ a, b"


def test_build_momentum_veto_result_json_and_markdown_aligned() -> None:
    class _M:
        r5 = 0.20
        volume_ratio_25d = 4.0
        overheat_flag = False

    rules = {
        "fomo_veto": [
            {
                "id": "fomo_volume_price_chase",
                "metric": "fomo_volume_price_chase",
                "threshold": 1.0,
                "message": "chase",
            }
        ]
    }
    vr = build_momentum_veto_result(_M(), VetoEngine(rules=rules))
    assert vr["triggered"] is True
    assert vr["rules"][0]["rule_id"] == "fomo_volume_price_chase"
    assert format_veto_table_cell(vr) == "⚠ fomo_volume_price_chase"
    assert momentum_breakdown_veto_context(_M)["fomo_volume_price_chase"] == 1.0

