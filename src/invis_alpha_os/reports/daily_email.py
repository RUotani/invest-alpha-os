"""Daily operator bundle → Japanese observation email (no trading advice)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
_DISCLAIMER_JA = (
    "このメールは観測・調査候補の整理であり、売買推奨・投資助言・発注指示ではありません。"
    " 自動売買は行いません。米国株キャッシュプレビューは既定ではオフ（明示 opt-in 時のみ）。"
)

_MISSING_JA = "未生成"
_EMPTY_JA = "該当なし"
_INSUFFICIENT_JA = "データ不足"

# Table header rows only (exact or prefix match after strip)
_JP_MOMENTUM_HEADER_MAP: tuple[tuple[str, str], ...] = (
    (
        "| # | Code / Name | Sv2 | Labels | r5 | r20 | r60 | HiDist | VolR | Veto |",
        "| # | コード / 銘柄名 | 状態 | シグナル | 騰落率(5日) | 騰落率(20日) | 騰落率(60日) | 高値圏 | 出来高状態 | メモ |",
    ),
    (
        "| Rank | Code | Sv2 | Key | r5 | r20 | r60 | HiDist | VolR | Flag | Watch | Bars src | Veto |",
        "| 順位 | コード | 状態 | シグナル | 騰落率(5日) | 騰落率(20日) | 騰落率(60日) | 高値圏 | 出来高状態 | フラグ | 注視 | データ源 | メモ |",
    ),
)

_US_PREVIEW_HEADER_MAP: tuple[tuple[str, str], ...] = (
    (
        "| symbol / name | latest_date | freshness_status | close | return_1d | return_5d | return_20d | volume_status | note |",
        "| コード / 銘柄名 | 最新日 | 状態 | 終値 | 騰落率(1日) | 騰落率(5日) | 騰落率(20日) | 出来高状態 | メモ |",
    ),
)

_PHRASE_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("stale — returns not used", "期限切れ — リターン計算には未使用"),
    ("Observation only — not buy/sell advice", "観測のみ — 売買推奨ではありません"),
    ("Not trading advice", "売買推奨ではありません"),
    ("No automatic trading", "自動売買なし"),
    ("fresh_enough", "十分に新しい"),
    ("freshness_unknown", "鮮度不明"),
    ("(operator_summary.md not found)", _MISSING_JA),
    ("(daily_us_cache_preview.md not found)", _MISSING_JA),
    ("(signals_us_cache_preview.md not found)", _MISSING_JA),
)


@dataclass(frozen=True)
class DailyEmailDraft:
    subject: str
    text_body: str
    html_body: str
    bundle_dir: Path
    report_date: str
    freshness_summary: str | None = None


def _read_optional(path: Path) -> str:
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return ""


def _extract_freshness(signals_md: str, operator_summary: str) -> str | None:
    for blob in (signals_md, operator_summary):
        m = re.search(r"stale\s*\*?\*?\s*0|stale\s+0", blob, re.I)
        if m:
            fe = re.search(r"fresh_enough\s*\*?\*?\s*16|fresh_enough\s+16", blob, re.I)
            if fe:
                return "期限切れ 0 / 十分に新しい 16"
    m2 = re.search(r"stale_count['\"]?\s*:\s*0", signals_md)
    if m2:
        return "期限切れ 0（詳細はバンドル参照）"
    return None


def _extract_between(md: str, start_pat: str, end_pat: str | None = None) -> str:
    m = re.search(start_pat, md, re.I | re.M)
    if not m:
        return ""
    rest = md[m.start() :]
    if end_pat:
        m2 = re.search(end_pat, rest[len(m.group(0)) :], re.I | re.M)
        if m2:
            return rest[: len(m.group(0)) + m2.start()].strip()
    return rest.strip()


def _jp_momentum_from_bundle(signals_md: str, daily_md: str) -> str:
    if "### US Cache Preview" in signals_md:
        jp = signals_md.split("### US Cache Preview", 1)[0].strip()
        if jp:
            return jp
    if signals_md.strip() and re.search(r"JP Watchlist|Momentum Signals", signals_md, re.I):
        return signals_md.strip()
    block = _extract_between(
        daily_md,
        r"## Momentum Signals — Cache Only",
        r"^## US Daily Bars",
    )
    if block:
        return block
    block = _extract_between(daily_md, r"## Japan Signals", r"^## ")
    return block.strip()


def _us_preview_from_bundle(signals_md: str, daily_md: str) -> str:
    if "### US Cache Preview" in signals_md:
        us = "### US Cache Preview" + signals_md.split("### US Cache Preview", 1)[1]
        return us.strip()
    block = _extract_between(daily_md, r"^## US Daily Bars", r"^## Momentum Signals — Mixed")
    if block:
        return block
    block = _extract_between(daily_md, r"^## US Daily Bars", None)
    return block.strip()


def _localize_markdown_block(md: str) -> str:
    if not md.strip():
        return _EMPTY_JA
    out_lines: list[str] = []
    for line in md.splitlines():
        stripped = line.strip()
        replaced = line
        for old, new in _JP_MOMENTUM_HEADER_MAP + _US_PREVIEW_HEADER_MAP:
            if stripped == old:
                replaced = new
                break
        for old, new in _PHRASE_REPLACEMENTS:
            if old in replaced:
                replaced = replaced.replace(old, new)
        if stripped == "—" or stripped == "-":
            pass
        out_lines.append(replaced)
    return "\n".join(out_lines)


def _build_summary(freshness: str | None, operator_summary: str) -> str:
    lines = ["- 観測バンドル: 生成済み"]
    if freshness:
        lines.append(f"- 鮮度サマリー: {freshness}")
    elif operator_summary.strip():
        lines.append("- 鮮度サマリー: データ不足（operator_summary から未検出）")
    else:
        lines.append(f"- 鮮度サマリー: {_INSUFFICIENT_JA}")
    if "J-Quants disabled" in operator_summary or "not configured" in operator_summary:
        lines.append("- J-Quants: 無効または未設定（本メールは cache / dry-run 観測）")
    return "\n".join(lines)


def _build_caveats(
    *,
    operator_summary: str,
    daily_preview: str,
    signals_preview: str,
) -> str:
    items: list[str] = []
    if not operator_summary.strip():
        items.append(f"- operator_summary.md: {_MISSING_JA}")
    if not daily_preview.strip():
        items.append(f"- daily_us_cache_preview.md: {_MISSING_JA}")
    if not signals_preview.strip():
        items.append(f"- signals_us_cache_preview.md: {_MISSING_JA}")
    if "synthetic" in signals_preview.lower() or "synthetic_dry_run" in signals_preview:
        items.append("- 日本株シグナル: synthetic dry-run モード（実データ観測ではありません）")
    if not items:
        return _EMPTY_JA
    return "\n".join(items)


def _text_to_html_body(text: str, *, title: str) -> str:
    escaped = _html_escape(text)
    return (
        f"<html><body>"
        f"<h1>{_html_escape(title)}</h1>"
        f"<p><em>{_html_escape(_DISCLAIMER_JA)}</em></p>"
        f"<pre style='font-family: sans-serif; white-space: pre-wrap;'>{escaped}</pre>"
        f"</body></html>"
    )


def build_daily_email_from_bundle(
    bundle_dir: Path,
    *,
    main_commit: str | None = None,
    report_date: str | None = None,
) -> DailyEmailDraft:
    bundle_dir = bundle_dir.resolve()
    run_date = report_date or bundle_dir.name
    operator_summary = _read_optional(bundle_dir / "operator_summary.md")
    daily_preview = _read_optional(bundle_dir / "daily_us_cache_preview.md")
    signals_preview = _read_optional(bundle_dir / "signals_us_cache_preview.md")

    freshness = _extract_freshness(signals_preview, operator_summary)
    if freshness:
        subject = f"[invest-alpha-os] 投資観測レポート {run_date} — {freshness}"
    else:
        subject = f"[invest-alpha-os] 投資観測レポート {run_date}"

    jp_block = _localize_markdown_block(_jp_momentum_from_bundle(signals_preview, daily_preview))
    us_block = _localize_markdown_block(_us_preview_from_bundle(signals_preview, daily_preview))
    summary = _build_summary(freshness, operator_summary)
    caveats = _build_caveats(
        operator_summary=operator_summary,
        daily_preview=daily_preview,
        signals_preview=signals_preview,
    )

    commit_line = f"- main コミット: `{main_commit}`" if main_commit else ""
    meta_lines = [
        f"- 日付: {run_date}",
        commit_line,
        f"- バンドル: `{bundle_dir}`",
        f"- 生成日（ローカル）: {date.today().isoformat()}",
    ]
    meta = "\n".join(line for line in meta_lines if line)

    text_parts = [
        f"投資観測レポート — {run_date}",
        "",
        _DISCLAIMER_JA,
        "",
        "## サマリー",
        summary,
        "",
        "## 日本株モメンタム観測",
        jp_block if jp_block.strip() and jp_block != _EMPTY_JA else _INSUFFICIENT_JA,
        "",
        "## 米国株キャッシュプレビュー",
        us_block if us_block.strip() and us_block != _EMPTY_JA else _INSUFFICIENT_JA,
        "",
        "## 注意・未完了項目",
        caveats,
        "",
        "## 生成情報",
        meta,
    ]
    text_body = "\n".join(text_parts)
    html_body = _text_to_html_body(text_body, title=f"投資観測レポート — {run_date}")

    return DailyEmailDraft(
        subject=subject,
        text_body=text_body,
        html_body=html_body,
        bundle_dir=bundle_dir,
        report_date=run_date,
        freshness_summary=freshness,
    )


def _html_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
