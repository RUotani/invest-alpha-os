from __future__ import annotations

from invis_alpha_os.product.weekly_candidate_brief_v0 import (
    CandidateCard,
    UnifiedCandidate,
    WeeklyCandidateBriefV0,
    format_weekly_candidate_brief_v0_copy,
)


def _candidate(*, symbol: str = "285A", name: str = "キオクシア") -> UnifiedCandidate:
    return UnifiedCandidate(
        market="jp",
        instrument_id=symbol,
        display_name=name,
        discovery_score=10,
        latest_date="2026-06-01",
        close=100.0,
        return_5d=0.02,
        return_20d=0.15,
        return_60d=0.20,
        labels=("rapid_mover_20d", "near_high"),
        categories=("rapid_mover",),
        data_quality="ok",
        reason="surfaced: near_high, rapid_mover_20d",
        themes=("memory",),
        volume_status="normal",
    )


def _positive_brief() -> WeeklyCandidateBriefV0:
    msft_card = CandidateCard(
        brief_type="top_pick",
        candidate=_candidate(symbol="MSFT", name="Microsoft"),
        reason="注目理由: クラウド需要は堅いが金利感応度を確認。",
        counter_evidence=("バリュエーション",),
        next_checks=("決算確認",),
    )
    kioxia_overheat = CandidateCard(
        brief_type="avoid",
        candidate=_candidate(symbol="285A", name="キオクシア"),
        reason="過熱: 追いかけ禁止。",
        counter_evidence=("割高感",),
        next_checks=("周辺候補",),
    )
    return WeeklyCandidateBriefV0(
        report_date="2026-06-06",
        generated_at_jp="t1",
        generated_at_us="t2",
        jp_scope="jp",
        us_scope="us",
        macro_summary="macro",
        top_picks=[msft_card],
        early_discovery_picks=[msft_card],
        overheated_leaders=[kioxia_overheat],
        rapid_movers=[
            CandidateCard(
                brief_type="rapid_mover",
                candidate=_candidate(symbol="NVDA", name="NVIDIA"),
                reason="急騰の観測理由: 出来高急増。",
                counter_evidence=("過熱",),
                next_checks=("反転確認",),
            )
        ],
        avoid_list=[
            CandidateCard(
                brief_type="avoid",
                candidate=_candidate(symbol="HYPE_E", name="Hype ETF"),
                reason="回避の観測理由: 高ボラ偏重。",
                counter_evidence=("veto相当",),
                next_checks=("veto理由確認",),
            )
        ],
    )


def test_candidate_positive_copy_has_concise_conclusion() -> None:
    body = format_weekly_candidate_brief_v0_copy(_positive_brief())

    assert "## 今週の結論（3行）" in body
    assert "初動・深掘り候補あり" in body
    assert "MSFT" in body
    assert "285A" in body
    assert "第1候補: 285A（キオクシア）" not in body
    investable = body.split("## 初動・深掘り候補", maxsplit=1)[1].split("## ", maxsplit=1)[0]
    overheat = body.split("## 過熱代表 / Do Not Chase", maxsplit=1)[1].split("## ", maxsplit=1)[0]
    assert "MSFT" in investable
    assert "285A" not in investable
    assert "285A" in overheat
    assert "これは売買指示ではありません" in body
    assert "深掘り候補: 2件。反証と次確認" not in body

    conclusion_start = body.index("## 今週の結論（3行）")
    next_section = body.find("\n## ", conclusion_start + 1)
    conclusion = body[conclusion_start:next_section] if next_section != -1 else body[conclusion_start:]
    for fixture_name in ("GRID_A", "ROBO_B", "MAT_C", "CASH_D"):
        assert fixture_name not in conclusion
