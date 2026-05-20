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

_TABLE_HEADER_MARKERS = frozenset(
    {
        "#",
        "Rank",
        "Code",
        "symbol / name",
        "コード / 銘柄名",
        "コード",
        "順位",
    }
)


@dataclass(frozen=True)
class _JpMomentumRow:
    rank: str
    code_name: str
    sv2: int
    labels: str
    r5: str
    r20: str
    r60: str
    veto: str


@dataclass(frozen=True)
class _UsPreviewRow:
    symbol_name: str
    latest_date: str
    freshness: str
    ret_1d: str
    ret_5d: str
    ret_20d: str
    note: str


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
    return _extract_between(daily_md, r"## Japan Signals", r"^## ").strip()


def _us_preview_from_bundle(signals_md: str, daily_md: str) -> str:
    if "### US Cache Preview" in signals_md:
        return ("### US Cache Preview" + signals_md.split("### US Cache Preview", 1)[1]).strip()
    block = _extract_between(daily_md, r"^## US Daily Bars", r"^## Momentum Signals — Mixed")
    if block:
        return block
    return _extract_between(daily_md, r"^## US Daily Bars", None).strip()


def _split_table_line(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _is_table_separator(line: str) -> bool:
    s = line.strip()
    return s.startswith("|---") or s.startswith("| ---")


def _parse_int_safe(value: str) -> int:
    try:
        return int(value)
    except ValueError:
        return 0


def _parse_pct(value: str) -> float | None:
    s = value.strip().replace("%", "").replace("+", "")
    if not s or s in ("—", "-"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _parse_jp_rows(md: str) -> list[_JpMomentumRow]:
    rows: list[_JpMomentumRow] = []
    for line in md.splitlines():
        if not line.strip().startswith("|") or _is_table_separator(line):
            continue
        cells = _split_table_line(line)
        if len(cells) < 6:
            continue
        lead = cells[0]
        if lead in _TABLE_HEADER_MARKERS or lead.lower() in ("rank", "code"):
            continue
        # JP watchlist: # | Code/Name | Sv2 | Labels | r5 | r20 | r60 | ...
        if lead.isdigit() and len(cells) >= 9:
            rows.append(
                _JpMomentumRow(
                    rank=lead,
                    code_name=cells[1],
                    sv2=_parse_int_safe(cells[2]),
                    labels=cells[3],
                    r5=cells[4],
                    r20=cells[5],
                    r60=cells[6],
                    veto=cells[8] if len(cells) > 8 else "—",
                )
            )
            continue
        # Cache-only: Rank | Code | Sv2 | Key | r5 | r20 | r60 | ... | Veto
        if lead.isdigit() and len(cells) >= 10:
            rows.append(
                _JpMomentumRow(
                    rank=lead,
                    code_name=cells[1],
                    sv2=_parse_int_safe(cells[2]),
                    labels=cells[3],
                    r5=cells[4],
                    r20=cells[5],
                    r60=cells[6],
                    veto=cells[-1],
                )
            )
    return rows


def _parse_us_rows(md: str) -> list[_UsPreviewRow]:
    rows: list[_UsPreviewRow] = []
    for line in md.splitlines():
        if not line.strip().startswith("|") or _is_table_separator(line):
            continue
        cells = _split_table_line(line)
        if len(cells) < 7:
            continue
        if cells[0] in _TABLE_HEADER_MARKERS or cells[0].startswith("symbol"):
            continue
        rows.append(
            _UsPreviewRow(
                symbol_name=cells[0],
                latest_date=cells[1],
                freshness=cells[2],
                ret_1d=cells[4] if len(cells) > 4 else "—",
                ret_5d=cells[5] if len(cells) > 5 else "—",
                ret_20d=cells[6] if len(cells) > 6 else "—",
                note=cells[8] if len(cells) > 8 else "",
            )
        )
    return rows


def _jp_comment(row: _JpMomentumRow) -> str:
    parts: list[str] = []
    labels_l = row.labels.lower()
    if row.sv2 >= 6:
        parts.append(f"モメンタム状態スコア {row.sv2}（相対上位）")
    if "high_52w_breakout" in labels_l or "breakout" in labels_l:
        parts.append("52週高値圏付近のブレイクアウト系ラベル")
    if "positive_20d_60d_momentum" in labels_l:
        parts.append("20日・60日方向のモメンタムが揃っている観測")
    if "overheat" in labels_l or "hard_momentum" in row.veto.lower():
        parts.append("過熱・警戒フラグあり（急伸後のボラティリティに注意）")
    r20 = _parse_pct(row.r20)
    if r20 is not None and r20 < 0:
        parts.append("20日騰落率はマイナス圏")
    if not parts:
        parts.append("大きなラベル変化は限定的。継続観測向き")
    return f"- **{row.code_name}**: " + "。".join(parts) + "。"


def _us_comment(row: _UsPreviewRow) -> str:
    parts: list[str] = []
    if "stale" in row.freshness.lower():
        parts.append("キャッシュ鮮度が期限切れ（リターンは参考扱い）")
    elif "fresh" in row.freshness.lower():
        parts.append(f"鮮度: {row.freshness}")
    r20 = _parse_pct(row.ret_20d)
    if r20 is not None and abs(r20) >= 10:
        parts.append(f"20日騰落率 {row.ret_20d} と変動が目立つ")
    elif r20 is not None:
        parts.append(f"20日騰落率 {row.ret_20d}")
    if row.note.strip():
        parts.append(row.note.strip())
    if not parts:
        parts.append("大きな変化シグナルは限定的")
    return f"- **{row.symbol_name}**: " + "。".join(parts) + "。"


def _build_today_highlights(
    jp_rows: list[_JpMomentumRow],
    us_rows: list[_UsPreviewRow],
    *,
    freshness: str | None,
    synthetic_jp: bool,
) -> str:
    lines: list[str] = [
        "- 本メールは当日スナップショットの整理です（前回送信との自動差分は未算出）。",
    ]
    if freshness:
        lines.append(f"- 米国キャッシュ鮮度: {freshness}。")
    if jp_rows:
        top = sorted(jp_rows, key=lambda r: (-r.sv2, r.rank))[:3]
        names = "、".join(r.code_name for r in top)
        lines.append(f"- 日本株ウォッチリスト上位（状態スコア順）: {names}。")
    else:
        lines.append("- 日本株テーブル: データ不足または未生成。")
    if synthetic_jp:
        lines.append("- 日本株は synthetic dry-run の可能性あり。実データ観測としては扱わないこと。")
    if us_rows:
        by_r20 = sorted(
            us_rows,
            key=lambda r: (_parse_pct(r.ret_20d) is not None, _parse_pct(r.ret_20d) or 0.0),
            reverse=True,
        )
        if by_r20:
            lines.append(
                f"- 米国キャッシュプレビューで20日騰落が相対的に大きい例: {by_r20[0].symbol_name}（{by_r20[0].ret_20d}）。"
            )
        stale_n = sum(1 for r in us_rows if "stale" in r.freshness.lower())
        if stale_n:
            lines.append(f"- 米国で期限切れ銘柄: {stale_n} 件（リターン指標は慎重に参照）。")
    else:
        lines.append("- 米国プレビュー: データ不足または未生成。")
    return "\n".join(lines)


def _build_symbol_comments(jp_rows: list[_JpMomentumRow], us_rows: list[_UsPreviewRow]) -> str:
    lines: list[str] = []
    if jp_rows:
        lines.append("**日本株（上位5件）**")
        for row in sorted(jp_rows, key=lambda r: (-r.sv2, r.rank))[:5]:
            lines.append(_jp_comment(row))
    else:
        lines.append(_INSUFFICIENT_JA)
    if us_rows:
        lines.append("")
        lines.append("**米国株（変動が目立つ上位3件）**")
        ranked = sorted(
            us_rows,
            key=lambda r: abs(_parse_pct(r.ret_20d) or 0.0),
            reverse=True,
        )[:3]
        for row in ranked:
            lines.append(_us_comment(row))
    return "\n".join(lines) if lines else _EMPTY_JA


def _build_watch_next(
    jp_rows: list[_JpMomentumRow],
    us_rows: list[_UsPreviewRow],
    caveats: str,
) -> str:
    lines = [
        "- 上位銘柄について: 決算・ニュース・出来高の異常を手動で確認（観測の補強）。",
        "- ラベルに overheat / breakout が付いた銘柄: 短期急伸後の反落リスクをメモ（判断材料であり推奨ではない）。",
    ]
    if us_rows and any("stale" in r.freshness.lower() for r in us_rows):
        lines.append("- 米国で期限切れ銘柄がある場合: キャッシュ更新または ingest 計画を別途確認。")
    if caveats != _EMPTY_JA:
        lines.append("- 下記「注意・未完了項目」の未解消項目を優先確認。")
    return "\n".join(lines)


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
        out_lines.append(replaced)
    return "\n".join(out_lines)


def _build_summary(
    freshness: str | None,
    operator_summary: str,
    *,
    jp_count: int,
    us_count: int,
) -> str:
    lines = [
        "- 観測バンドル: 生成済み",
        f"- 日本株ランキング行数: {jp_count}",
        f"- 米国プレビュー行数: {us_count}",
    ]
    if freshness:
        lines.append(f"- 鮮度サマリー: {freshness}")
    elif operator_summary.strip():
        lines.append("- 鮮度サマリー: バンドルから未検出")
    else:
        lines.append(f"- 鮮度サマリー: {_INSUFFICIENT_JA}")
    if "J-Quants disabled" in operator_summary or "not configured" in operator_summary:
        lines.append("- J-Quants: 無効または未設定（cache / dry-run 観測）")
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
        items.append("- 日本株シグナル: synthetic dry-run モード（実データ観測ではない）")
    items.append("- 添付ファイル: なし（本文 HTML/テキストのみ）")
    return "\n".join(items) if items else _EMPTY_JA


def _text_to_html_body(text: str, *, title: str) -> str:
    parts: list[str] = [
        "<html><body>",
        f"<h1>{_html_escape(title)}</h1>",
        f"<p><em>{_html_escape(_DISCLAIMER_JA)}</em></p>",
    ]
    in_list = False
    for line in text.splitlines():
        if line.startswith("## "):
            if in_list:
                parts.append("</ul>")
                in_list = False
            parts.append(f"<h2>{_html_escape(line[3:])}</h2>")
            continue
        if line.startswith("- "):
            if not in_list:
                parts.append("<ul>")
                in_list = True
            body = _html_escape(line[2:])
            body = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", body)
            parts.append(f"<li>{body}</li>")
            continue
        if in_list:
            parts.append("</ul>")
            in_list = False
        if line.startswith("|"):
            parts.append(
                f"<pre style='font-size:12px;overflow-x:auto'>{_html_escape(line)}</pre>"
            )
            continue
        if not line.strip():
            parts.append("<br/>")
            continue
        body = _html_escape(line)
        body = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", body)
        parts.append(f"<p>{body}</p>")
    if in_list:
        parts.append("</ul>")
    parts.append("</body></html>")
    return "".join(parts)


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
    subject = (
        f"[invest-alpha-os] 投資観測レポート {run_date} — {freshness}"
        if freshness
        else f"[invest-alpha-os] 投資観測レポート {run_date}"
    )

    jp_raw = _jp_momentum_from_bundle(signals_preview, daily_preview)
    us_raw = _us_preview_from_bundle(signals_preview, daily_preview)
    jp_rows = _parse_jp_rows(jp_raw)
    us_rows = _parse_us_rows(us_raw)
    synthetic_jp = "synthetic" in signals_preview.lower()

    jp_block = _localize_markdown_block(jp_raw)
    us_block = _localize_markdown_block(us_raw)
    summary = _build_summary(
        freshness, operator_summary, jp_count=len(jp_rows), us_count=len(us_rows)
    )
    highlights = _build_today_highlights(
        jp_rows, us_rows, freshness=freshness, synthetic_jp=synthetic_jp
    )
    symbol_comments = _build_symbol_comments(jp_rows, us_rows)
    caveats = _build_caveats(
        operator_summary=operator_summary,
        daily_preview=daily_preview,
        signals_preview=signals_preview,
    )
    watch_next = _build_watch_next(jp_rows, us_rows, caveats)

    commit_line = f"- main コミット: `{main_commit}`" if main_commit else ""
    meta = "\n".join(
        line
        for line in (
            f"- 日付: {run_date}",
            commit_line,
            f"- バンドル: `{bundle_dir}`",
            f"- 生成日（ローカル）: {date.today().isoformat()}",
        )
        if line
    )

    text_parts = [
        f"投資観測レポート — {run_date}",
        "",
        "## サマリー",
        summary,
        "",
        "## 今日の注目ポイント",
        highlights,
        "",
        "## 日本株モメンタム観測",
        "以下は cache / dry-run 由来の観測テーブルです。数値のみでなく、上記注目ポイントと銘柄別コメントを併読してください。",
        "",
        jp_block if jp_block.strip() and jp_block != _EMPTY_JA else _INSUFFICIENT_JA,
        "",
        "## 米国株キャッシュプレビュー",
        "opt-in プレビュー。鮮度・リターンは観測補助であり、売買判断ではありません。",
        "",
        us_block if us_block.strip() and us_block != _EMPTY_JA else _INSUFFICIENT_JA,
        "",
        "## 銘柄別コメント",
        symbol_comments,
        "",
        "## 注意・未完了項目",
        caveats,
        "",
        "## 次に確認すること",
        watch_next,
        "",
        "## 生成情報",
        meta,
        "",
        "## 免責",
        _DISCLAIMER_JA,
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
