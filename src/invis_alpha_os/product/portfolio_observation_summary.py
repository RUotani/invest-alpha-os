"""Read-only portfolio ↔ observation linkage summary (observation only)."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from invis_alpha_os.config.paths import OUTPUTS_DIR, ROOT_DIR
from invis_alpha_os.portfolio.shadow_portfolio import ShadowPortfolioService


@dataclass(frozen=True)
class PortfolioObservationSummary:
    shadow_path: str
    observation_path: str
    shadow_position_count: int
    observation_row_count: int
    positions_with_evidence_ids: int
    positions_with_resolved_links: int
    unresolved_evidence_ids: list[str]
    positions: list[dict[str, Any]]
    by_symbol: dict[str, int]
    by_tag: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "shadow_path": self.shadow_path,
            "observation_path": self.observation_path,
            "shadow_position_count": self.shadow_position_count,
            "observation_row_count": self.observation_row_count,
            "positions_with_evidence_ids": self.positions_with_evidence_ids,
            "positions_with_resolved_links": self.positions_with_resolved_links,
            "unresolved_evidence_ids": self.unresolved_evidence_ids,
            "positions": self.positions,
            "by_symbol": self.by_symbol,
            "by_tag": self.by_tag,
        }


def build_portfolio_observation_summary(
    *,
    path_base: Path | None = None,
    shadow_path: Path | None = None,
    observation_path: Path | None = None,
) -> PortfolioObservationSummary:
    root = path_base or ROOT_DIR
    shadow = shadow_path or (OUTPUTS_DIR / "shadow_portfolio" / "positions.jsonl")
    obs_path = observation_path or (
        OUTPUTS_DIR / "observation_log" / "observation_log.jsonl"
    )
    portfolio = ShadowPortfolioService(shadow)
    positions = portfolio.list_positions()
    obs_ids: set[str] = set()
    obs_count = 0
    if obs_path.is_file():
        for line in obs_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(row, dict):
                continue
            obs_count += 1
            rid = row.get("id")
            if rid:
                obs_ids.add(str(rid))

    position_rows: list[dict[str, Any]] = []
    with_evidence = 0
    resolved = 0
    unresolved: set[str] = set()
    symbol_counts: Counter[str] = Counter()
    tag_counts: Counter[str] = Counter()
    for pos in positions:
        sym_key = str(pos.symbol or "").strip().upper() or "(empty)"
        symbol_counts[sym_key] += 1
        for tag in pos.tags or []:
            tag_counts[str(tag)] += 1
        evidence = list(pos.thesis_evidence_ids or [])
        if evidence:
            with_evidence += 1
        matched = [eid for eid in evidence if eid in obs_ids]
        missing = [eid for eid in evidence if eid not in obs_ids]
        if evidence and matched:
            resolved += 1
        unresolved.update(missing)
        position_rows.append(
            {
                "id": pos.id,
                "symbol": pos.symbol,
                "thesis_evidence_ids": evidence,
                "resolved_observation_ids": matched,
                "unresolved_evidence_ids": missing,
                "tags": list(pos.tags or []),
            }
        )

    def _rel(p: Path) -> str:
        try:
            return str(p.relative_to(root))
        except ValueError:
            return str(p)

    return PortfolioObservationSummary(
        shadow_path=_rel(shadow),
        observation_path=_rel(obs_path),
        shadow_position_count=len(positions),
        observation_row_count=obs_count,
        positions_with_evidence_ids=with_evidence,
        positions_with_resolved_links=resolved,
        unresolved_evidence_ids=sorted(unresolved),
        positions=position_rows,
        by_symbol=dict(sorted(symbol_counts.items())),
        by_tag=dict(sorted(tag_counts.items())),
    )


def format_portfolio_observation_summary_markdown(summary: PortfolioObservationSummary) -> str:
    lines = [
        "# Portfolio observation summary (read-only)",
        "",
        f"- shadow: `{summary.shadow_path}` ({summary.shadow_position_count} positions)",
        f"- observation_log: `{summary.observation_path}` ({summary.observation_row_count} rows)",
        f"- positions with thesis_evidence_ids: {summary.positions_with_evidence_ids}",
        f"- positions with ≥1 resolved observation link: {summary.positions_with_resolved_links}",
        "",
    ]
    if summary.by_symbol:
        lines.extend(["## Exposure by symbol", ""])
        for sym, count in summary.by_symbol.items():
            lines.append(f"- {sym}: {count}")
        lines.append("")
    if summary.by_tag:
        lines.extend(["## Exposure by tag", ""])
        for tag, count in summary.by_tag.items():
            lines.append(f"- {tag}: {count}")
        lines.append("")
    if summary.unresolved_evidence_ids:
        lines.append("## Unresolved evidence IDs")
        lines.append("")
        for eid in summary.unresolved_evidence_ids[:20]:
            lines.append(f"- `{eid}`")
        if len(summary.unresolved_evidence_ids) > 20:
            lines.append(f"- … and {len(summary.unresolved_evidence_ids) - 20} more")
        lines.append("")
    lines.extend(["## Positions", ""])
    if not summary.positions:
        lines.append("_No shadow positions._")
    else:
        for row in summary.positions:
            sym = row.get("symbol", "")
            pid = row.get("id", "")
            resolved = row.get("resolved_observation_ids") or []
            lines.append(f"- **{sym}** (`{pid}`): {len(resolved)} linked observation(s)")
    lines.append("")
    return "\n".join(lines)


def format_portfolio_observation_summary_json(summary: PortfolioObservationSummary) -> str:
    return json.dumps(summary.to_dict(), ensure_ascii=False, indent=2)
