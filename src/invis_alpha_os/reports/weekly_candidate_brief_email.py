"""Weekly Candidate Brief -> Gmail preview/test-send drafts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from html import escape
import re

from invis_alpha_os.reports.weekly_candidate_brief_quant_metrics import (
    compute_candidate_quant_metrics,
    fmt_num,
    fmt_pct,
)

from invis_alpha_os.portfolio.target_allocation_gap_calculator_v82 import (
    compute_target_allocation_gap_from_portfolio_context_v82,
    format_target_allocation_gap_email_3_lines_v82,
)
from invis_alpha_os.product.weekly_candidate_brief_v0 import PORTFOLIO_CONTEXT_V81
from invis_alpha_os.product.weekly_email_shared_view_model_v96 import (
    extract_weekly_shared_view_model_from_copy_v96,
    render_weekly_shared_view_model_email_text_v96,
)

_TABLE_ROW_RE = re.compile(
    r"^\|\s*(?P<rank>\d+)\s*\|\s*(?P<symbol>[^|]+)\|\s*(?P<name>[^|]+)\|\s*(?P<market>[^|]+)\|\s*(?P<kind>[^|]+)\|\s*(?P<reason>[^|]+)\|\s*$"
)


@dataclass(frozen=True)
class WeeklyCandidateBriefEmailDraft:
    subject: str
    text_body: str
    html_body: str | None = None


def build_weekly_candidate_brief_email_subject(report_date: str) -> str:
    return f"[TEST][invest-alpha-os] Weekly Candidate Brief {report_date}"


@dataclass(frozen=True)
class CandidateDigest:
    rank: int
    symbol: str
    name: str
    market: str
    kind: str
    short_reason: str
    counter_evidence: str
    next_checks: str


EMAIL_PORTFOLIO_CONTEXT_V85 = "現金11.7% / 個別株19.6% / 株式系67.8%"

EMAIL_ALLOWED_ACTIONS_V85: tuple[str, ...] = (
    "候補0件の理由、coverage不足、score未達、veto理由を確認する",
    "監視候補・整理候補・高ボラ枠の根拠確認を進める",
    "現金11.7%から最低15%、できれば20%方向へ戻す前提で判断を記録する",
)

EMAIL_SUPPRESSED_ACTIONS_V85: tuple[str, ...] = (
    "根拠不足の新規個別株・高ベータ枠を追加しない",
    "個別株19.6%のまま、個別株候補を強い新規リスク候補扱いしない",
    "データ不足候補をcoverage・価格・score内訳なしで深掘り対象にしない",
)

EMAIL_NEXT_CHECKS_V85: tuple[str, ...] = (
    "現金比率が15%未満で止まっていないか",
    "株式系67.8%と個別株19.6%に重複リスク・整理候補がないか",
    "次回weekly runで候補0件の理由が改善しているか",
)

EMAIL_CLEANUP_PRIORITY_NOTE_V83 = "このスコアは売却指示ではなく、次に確認すべき整理・監視優先度です。"

EMAIL_CLEANUP_PRIORITY_ROWS_V83: tuple[tuple[str, int, str, str], ...] = (
    (
        "個別株枠",
        4,
        "19.6%で10〜15%方向の目安を上回り、現金11.7%も不足",
        "新規追加より整理・監視を優先",
    ),
    (
        "株式系重複リスク",
        4,
        "株式系67.8%でINDEXと個別株の同方向リスクが積み上がりやすい",
        "重複テーマ・セクター偏りを確認",
    ),
    (
        "高ボラ枠",
        3,
        "高ベータ枠1.3%は小さいが、現金不足下では追加リスクを抑制",
        "追加せず監視",
    ),
    (
        "データ不足候補",
        3,
        "coverage / score / veto理由の確認が先",
        "深掘り前に根拠を補完",
    ),
)

_TARGET_ALLOCATION_GAP_V82 = compute_target_allocation_gap_from_portfolio_context_v82(PORTFOLIO_CONTEXT_V81)
EMAIL_TARGET_ALLOCATION_GAP_3_LINES_V82: tuple[str, str, str] = format_target_allocation_gap_email_3_lines_v82(
    _TARGET_ALLOCATION_GAP_V82
)


def _parse_top_candidates(copy_body: str) -> list[CandidateDigest]:
    lines = [x.rstrip() for x in copy_body.splitlines()]
    by_rank: dict[int, dict[str, str]] = {}
    in_table = False
    in_memo = False
    current_rank: int | None = None

    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if line.startswith("| Rank |") or line.startswith("| 順位 |"):
            in_table = True
            continue
        if in_table and line.startswith("|---"):
            continue
        if in_table and line.startswith("|"):
            m = _TABLE_ROW_RE.match(line)
            if not m:
                continue
            r = int(m.group("rank"))
            by_rank[r] = {
                "symbol": m.group("symbol").strip(),
                "name": m.group("name").strip(),
                "market": m.group("market").strip(),
                "kind": m.group("kind").strip(),
                "reason": m.group("reason").strip(),
                "counter": "キャッシュ内にデータなし",
                "next": "次回データ更新で要確認",
            }
            continue
        if line.startswith("## 候補別メモ"):
            in_memo = True
            in_table = False
            continue
        if in_memo and line.startswith("### "):
            m = re.match(r"^###\s*(\d+)\.\s*", line)
            current_rank = int(m.group(1)) if m else None
            continue
        if in_memo and current_rank is not None and line.startswith("- 反証:"):
            if current_rank in by_rank:
                by_rank[current_rank]["counter"] = line.split(":", 1)[1].strip() or "キャッシュ内にデータなし"
            continue
        if in_memo and current_rank is not None and line.startswith("- 次確認:"):
            if current_rank in by_rank:
                by_rank[current_rank]["next"] = line.split(":", 1)[1].strip() or "次回データ更新で要確認"

    out: list[CandidateDigest] = []
    for r in sorted(by_rank.keys()):
        row = by_rank[r]
        out.append(
            CandidateDigest(
                rank=r,
                symbol=row["symbol"],
                name=row["name"],
                market=row["market"],
                kind=row["kind"],
                short_reason=row["reason"],
                counter_evidence=row["counter"],
                next_checks=row["next"],
            )
        )
    return out


def _extract_candidate_zero_reason_notes(copy_body: str) -> tuple[str, str] | None:
    reason_line = ""
    next_line = ""
    for raw in copy_body.splitlines():
        line = raw.strip()
        if line.startswith("- 候補0件の主因:"):
            reason_line = line.removeprefix("- ").strip()
        elif line.startswith("- 次確認:"):
            next_line = line.removeprefix("- ").strip()
    if not reason_line and not next_line:
        return None
    if not reason_line:
        reason_line = "候補0件の主因: coverage/score/vetoの内訳を確認"
    if not next_line:
        next_line = "次確認: 価格・出来高・期間・score内訳・veto理由"
    return reason_line, next_line


def _extract_pipeline_trace_notes(copy_body: str) -> tuple[str, str] | None:
    summary_line = ""
    main_reason_line = ""
    for raw in copy_body.splitlines():
        line = raw.strip()
        if line.startswith("- 候補パイプライン:"):
            summary_line = line.removeprefix("- ").strip()
        elif line.startswith("- 主因:"):
            main_reason_line = line.removeprefix("- ").strip()
    if not summary_line and not main_reason_line:
        return None
    if not summary_line:
        summary_line = "候補パイプライン: 入力/coverage不足/score未達/veto/深掘り可能を確認"
    if not main_reason_line:
        main_reason_line = "主因: coverage不足。次確認: 価格・出来高・期間・score内訳・veto理由。"
    return summary_line, main_reason_line


def _extract_score_veto_summary_notes(copy_body: str) -> tuple[str, ...]:
    model = extract_weekly_shared_view_model_from_copy_v96(copy_body)
    return model.score_veto_summary_lines


def _extract_monthly_input_summary_notes(copy_body: str) -> tuple[str, ...]:
    model = extract_weekly_shared_view_model_from_copy_v96(copy_body)
    return model.monthly_input_summary_lines


def _extend_text_action_checklist(lines: list[str], *, zero_reason_notes: tuple[str, str] | None) -> None:
    lines.extend(
        [
            "",
            "## 今週の行動チェックリスト",
            f"- ポートフォリオ前提: {EMAIL_PORTFOLIO_CONTEXT_V85}",
            *[f"- {x}" for x in EMAIL_TARGET_ALLOCATION_GAP_3_LINES_V82],
            "",
            "### 今週やってよいこと",
        ]
    )
    lines.extend(f"- {item}" for item in EMAIL_ALLOWED_ACTIONS_V85)
    lines.append("- 整理・監視優先度スコアが高い枠の根拠を確認する")
    lines.extend(["", "### 今週やらないこと"])
    lines.extend(f"- {item}" for item in EMAIL_SUPPRESSED_ACTIONS_V85)
    lines.append("- 整理・監視優先度が高い枠と同じリスクを新規に増やさない")
    lines.extend(["", "### 次に確認すること"])
    lines.extend(f"- {item}" for item in EMAIL_NEXT_CHECKS_V85)
    lines.append("- score 4以上の枠がどの制約に集中しているか")
    lines.extend(
        [
            "",
            "### 候補0件の意味",
            "- 候補0件はレポート失敗ではありません。",
            "- 現金不足・データ不足・条件未達のため、新規リスクを増やさない判断材料です。",
        ]
    )
    if zero_reason_notes:
        reason_line, next_line = zero_reason_notes
        lines.extend([f"- {reason_line}", f"- {next_line}"])
    lines.extend(
        [
            "- veto該当0件でも、直ちに新規追加判断には進まず、coverage/scoreの再確認を優先します。",
            "",
        ]
    )


def _extend_text_cleanup_priority(lines: list[str]) -> None:
    lines.extend(["", "## 整理・監視優先度", f"- {EMAIL_CLEANUP_PRIORITY_NOTE_V83}"])
    for target, score, reason, treatment in EMAIL_CLEANUP_PRIORITY_ROWS_V83:
        lines.append(f"- {target}: {score} / 5 — {reason}。{treatment}。")
    lines.append("")


def _html_list(items: tuple[str, ...]) -> str:
    return "<ul style='margin:0 0 10px 18px;padding:0;'>" + "".join(
        f"<li>{escape(item)}</li>" for item in items
    ) + "</ul>"


def _append_html_action_checklist(parts: list[str], *, zero_reason_notes: tuple[str, str] | None) -> None:
    short_note = ""
    if zero_reason_notes:
        reason_line, next_line = zero_reason_notes
        short_note = (
            "<ul style='margin:6px 0 0 18px;padding:0;'>"
            f"<li>{escape(reason_line)}</li>"
            f"<li>{escape(next_line)}</li>"
            "</ul>"
        )
    parts.extend(
        [
            "<h2 style='margin:14px 0 8px;'>今週の行動チェックリスト</h2>",
            "<div style='display:block;background:#ffffff;border:1px solid #e5e7eb;border-radius:8px;padding:12px;margin:10px 0;'>",
            f"<p style='margin:0 0 8px;'><strong>ポートフォリオ前提:</strong> {escape(EMAIL_PORTFOLIO_CONTEXT_V85)}</p>",
            _html_list(EMAIL_TARGET_ALLOCATION_GAP_3_LINES_V82),
            "<h3 style='margin:0 0 6px;'>今週やってよいこと</h3>",
            _html_list(EMAIL_ALLOWED_ACTIONS_V85),
            "<h3 style='margin:8px 0 6px;'>今週やらないこと</h3>",
            _html_list(EMAIL_SUPPRESSED_ACTIONS_V85),
            "<h3 style='margin:8px 0 6px;'>次に確認すること</h3>",
            _html_list(EMAIL_NEXT_CHECKS_V85),
            "<p style='margin:8px 0 0;'>候補0件はレポート失敗ではなく、現金不足・データ不足・条件未達による抑制判断です。</p>",
            short_note,
            "<p style='margin:8px 0 0;'>veto該当0件でも、直ちに新規追加判断には進まず、coverage/scoreの再確認を優先します。</p>",
            "</div>",
        ]
    )


def _append_html_cleanup_priority(parts: list[str]) -> None:
    items = "".join(
        "<li>"
        f"<strong>{escape(target)}: {score} / 5</strong> — {escape(reason)}。{escape(treatment)}。"
        "</li>"
        for target, score, reason, treatment in EMAIL_CLEANUP_PRIORITY_ROWS_V83
    )
    parts.extend(
        [
            "<h2 style='margin:14px 0 8px;'>整理・監視優先度</h2>",
            "<div style='display:block;background:#ffffff;border:1px solid #e5e7eb;border-radius:8px;padding:12px;margin:10px 0;'>",
            f"<p style='margin:0 0 8px;'>{escape(EMAIL_CLEANUP_PRIORITY_NOTE_V83)}</p>",
            f"<ul style='margin:0 0 0 18px;padding:0;'>{items}</ul>",
            "</div>",
        ]
    )


def _build_rich_text_body(
    *,
    report_date: str,
    generated_at: str,
    candidates: list[CandidateDigest],
    zero_reason_notes: tuple[str, str] | None,
    pipeline_trace_notes: tuple[str, str] | None,
    score_veto_notes: tuple[str, ...],
    monthly_input_notes: tuple[str, ...],
) -> str:
    lines: list[str] = [
        "テストメール",
        f"レポート日: {report_date}",
        f"生成日時: {generated_at}",
        "注意書き: 投資助言ではなく、観測・検証用の情報です。",
        "",
        "## 要約",
        f"- 注目候補数: {len(candidates)}",
        "- 主目的: 次の調査候補を絞り込むための観測",
        "- 安全方針: 観測のみ（実行指示なし）",
        "",
        "## 候補パイプライン（短縮）",
    ]
    if pipeline_trace_notes:
        lines.extend([f"- {pipeline_trace_notes[0]}", f"- {pipeline_trace_notes[1]}"])
    else:
        lines.append("- 候補パイプライン要約: copy-ready側のtrace sectionを確認してください。")
    lines.extend(["", "## Score / Veto（短縮）"])
    if score_veto_notes:
        lines.extend(f"- {note}" for note in score_veto_notes)
    else:
        lines.append("- Score/Veto: copy-ready側の統合サマリーを確認してください。")
    lines.extend(["", "## Monthly Input Consistency（短縮）"])
    if monthly_input_notes:
        lines.extend(f"- {note}" for note in monthly_input_notes)
    else:
        lines.append("- Monthly Input: copy-ready側の共有要約を確認してください。")
    lines.extend(
        [
            "",
        "## 注目候補",
        ]
    )
    if not candidates:
        lines.extend(
            [
                "- 強い新規リスク候補: 0件",
                "- 理由: データ品質・coverage・score条件を同時に満たす候補がありません。",
                "- 判断方針: 現金比率が低い前提で、新規リスク追加より監視・整理・現金回復を優先します。",
            ]
        )
    _extend_text_action_checklist(lines, zero_reason_notes=zero_reason_notes)
    _extend_text_cleanup_priority(lines)
    for c in candidates:
        qm = compute_candidate_quant_metrics(symbol=c.symbol, market=c.market, report_date=report_date)
        momentum_q: list[str] = []
        counter_q: list[str] = []
        if qm.dist_ma_25_pct is not None and qm.dist_ma_25_pct > 0:
            momentum_q.append("終値が25日移動平均線を上回る")
        if qm.dist_ma_75_pct is not None and qm.dist_ma_75_pct > 0:
            momentum_q.append("終値が75日移動平均線を上回る")
        if qm.ret_20d_pct is not None and qm.ret_20d_pct > 0:
            momentum_q.append("20日騰落率がプラス")
        if qm.ret_60d_pct is not None and qm.ret_60d_pct > 0:
            momentum_q.append("60日騰落率がプラス")
        if qm.volume_ratio_20d is not None and qm.volume_ratio_20d >= 1.5:
            momentum_q.append("出来高倍率が1.5x超")
        if qm.dist_ma_25_pct is not None and qm.dist_ma_25_pct < 0:
            counter_q.append("終値が25日移動平均線を下回る")
        if qm.dist_ma_25_pct is not None and qm.dist_ma_25_pct > 0.12:
            counter_q.append("25日移動平均線からの乖離が+12%超（反落余地）")
        if qm.ret_60d_pct is not None and qm.ret_60d_pct < 0:
            counter_q.append("60日騰落率がマイナス")
        if qm.freshness_label.startswith("要更新"):
            counter_q.append(qm.freshness_label)
        if qm.missing_reason:
            counter_q.append(qm.missing_reason)
        lines.extend(
            [
                "",
                f"### {c.rank}. {c.symbol} — {c.name}",
                f"- 市場: {c.market}",
                f"- 候補種別: {c.kind}",
                f"- 短期理由: {c.short_reason}",
                "",
                "#### 移動平均線の位置づけ",
                f"- 25D移動平均線: {fmt_num(qm.ma_25)}（乖離 {fmt_pct(qm.dist_ma_25_pct)}）",
                f"- 75D移動平均線: {fmt_num(qm.ma_75)}（乖離 {fmt_pct(qm.dist_ma_75_pct)}）",
                f"- 200D移動平均線: {fmt_num(qm.ma_200)}（乖離 {fmt_pct(qm.dist_ma_200_pct)}）",
                "- 解釈: キャッシュ由来のため、データ鮮度と合わせて確認してください",
                "",
                "#### 定量スナップショット",
                f"- 直近終値: {fmt_num(qm.latest_close)}",
                f"- 直近データ日: {qm.latest_bar_date or 'キャッシュ内にデータなし'}",
                f"- データ鮮度: {qm.freshness_label}",
                f"- 騰落率: 5D {fmt_pct(qm.ret_5d_pct)}, 20D {fmt_pct(qm.ret_20d_pct)}, 60D {fmt_pct(qm.ret_60d_pct)}",
                f"- 52週レンジ: 高値 {fmt_num(qm.high_52w)}（高値から {fmt_pct(qm.dist_52w_high_pct)}）, 安値 {fmt_num(qm.low_52w)}（安値から {fmt_pct(qm.dist_52w_low_pct)}）",
                f"- 出来高: 直近 {fmt_num(qm.latest_volume, 0)}, 20D平均 {fmt_num(qm.avg_volume_20d, 0)}, 出来高倍率 {fmt_num(qm.volume_ratio_20d)}x",
                "",
                "#### モメンタム根拠",
                f"- {c.short_reason}",
                f"- 定量根拠: {', '.join(momentum_q) if momentum_q else 'キャッシュ内にデータなし'}",
                "- トレンド継続性は次回データ更新でも確認",
                "",
                "#### 反証・下落リスク",
                f"- {c.counter_evidence}",
                f"- 定量リスク: {', '.join(counter_q[:2]) if counter_q else 'キャッシュ内にデータなし'}",
                "- データ不足時はトレンド悪化を見落とす可能性がある",
                "",
                "#### 次に確認すること",
                f"- {c.next_checks}",
                "- 深掘り前に直近データ鮮度を再確認",
                "",
                "#### 情報ソース",
                f"- 市場データソース: {qm.source}",
                "- シグナルソース: weekly candidate brief score + momentum labels",
                f"- レポート日: {report_date}",
                f"- 生成日時: {generated_at}",
                f"- データ不足理由: {qm.missing_reason or 'なし'}",
            ]
        )
    lines.extend(
        [
            "",
            "## Footer / Safety Notes",
            "- 観測・検証用のみ",
            "- このメールはGmail表示確認用のテスト出力です",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def _build_rich_html_body(
    *,
    report_date: str,
    generated_at: str,
    candidates: list[CandidateDigest],
    footer: str,
    zero_reason_notes: tuple[str, str] | None,
    pipeline_trace_notes: tuple[str, str] | None,
    score_veto_notes: tuple[str, ...],
    monthly_input_notes: tuple[str, ...],
) -> str:
    pipeline_list = ""
    if pipeline_trace_notes:
        pipeline_list = (
            "<ul style='margin:0 0 10px 18px;padding:0;'>"
            f"<li>{escape(pipeline_trace_notes[0])}</li>"
            f"<li>{escape(pipeline_trace_notes[1])}</li>"
            "</ul>"
        )
    score_veto_list = ""
    if score_veto_notes:
        score_veto_list = "<ul style='margin:0 0 10px 18px;padding:0;'>" + "".join(
            f"<li>{escape(note)}</li>" for note in score_veto_notes
        ) + "</ul>"
    monthly_input_list = ""
    if monthly_input_notes:
        monthly_input_list = "<ul style='margin:0 0 10px 18px;padding:0;'>" + "".join(
            f"<li>{escape(note)}</li>" for note in monthly_input_notes
        ) + "</ul>"
    parts: list[str] = [
        "<html><body style='margin:0;padding:0;background:#f8fafc;color:#111827;'>",
        "<div style='max-width:680px;margin:0 auto;padding:16px;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif;line-height:1.55;'>",
        "<div style='background:#fff3cd;border:1px solid #ffe69c;border-radius:8px;padding:12px;margin-bottom:12px;'>",
        "<strong>テストメール</strong><br>",
        f"レポート日: {escape(report_date)}<br>",
        f"生成日時: {escape(generated_at)}<br>",
        "注意書き: 投資助言ではなく、観測・検証用の情報です。",
        "</div>",
        "<h2 style='margin:10px 0 6px;'>要約</h2>",
        f"<p style='margin:0 0 10px;'>注目候補数: {len(candidates)} / 観測ベースの候補抽出</p>",
        "<h2 style='margin:14px 0 8px;'>候補パイプライン（短縮）</h2>",
        pipeline_list or "<p style='margin:0 0 10px;'>候補パイプライン要約: copy-ready側のtrace sectionを確認してください。</p>",
        "<h2 style='margin:14px 0 8px;'>Score / Veto（短縮）</h2>",
        score_veto_list or "<p style='margin:0 0 10px;'>Score/Veto: copy-ready側の統合サマリーを確認してください。</p>",
        "<h2 style='margin:14px 0 8px;'>Monthly Input Consistency（短縮）</h2>",
        monthly_input_list or "<p style='margin:0 0 10px;'>Monthly Input: copy-ready側の共有要約を確認してください。</p>",
        "<h2 style='margin:14px 0 8px;'>注目候補</h2>",
    ]
    if not candidates:
        parts.extend(
            [
                "<div style='background:#ffffff;border:1px solid #e5e7eb;border-radius:8px;padding:12px;margin:10px 0;'>",
                "<p style='margin:0 0 6px;'><strong>強い新規リスク候補: 0件</strong></p>",
                "<p style='margin:0 0 6px;'>データ品質・coverage・score条件を同時に満たす候補がありません。</p>",
                "<p style='margin:0;'>現金比率が低い前提で、新規リスク追加より監視・整理・現金回復を優先します。</p>",
                "</div>",
            ]
        )
    _append_html_action_checklist(parts, zero_reason_notes=zero_reason_notes)
    _append_html_cleanup_priority(parts)
    for c in candidates:
        qm = compute_candidate_quant_metrics(symbol=c.symbol, market=c.market, report_date=report_date)
        parts.extend(
            [
                "<div style='background:#ffffff;border:1px solid #e5e7eb;border-radius:10px;padding:12px;margin:10px 0;'>",
                f"<h3 style='margin:0 0 6px;'>{c.rank}. {escape(c.symbol)} - {escape(c.name)}</h3>",
                f"<p style='margin:0 0 8px;'><strong>市場:</strong> {escape(c.market)} / <strong>種別:</strong> {escape(c.kind)}</p>",
                f"<p style='margin:0 0 8px;'><strong>短期理由:</strong> {escape(c.short_reason)}</p>",
                "<h4 style='margin:8px 0 4px;'>移動平均線の位置づけ</h4>",
                f"<ul style='margin:0 0 8px 18px;padding:0;'><li>25D移動平均線: {escape(fmt_num(qm.ma_25))}（乖離 {escape(fmt_pct(qm.dist_ma_25_pct))}）</li><li>75D移動平均線: {escape(fmt_num(qm.ma_75))}（乖離 {escape(fmt_pct(qm.dist_ma_75_pct))}）</li><li>200D移動平均線: {escape(fmt_num(qm.ma_200))}（乖離 {escape(fmt_pct(qm.dist_ma_200_pct))}）</li><li>解釈: キャッシュ由来のため、データ鮮度と合わせて確認してください</li></ul>",
                "<h4 style='margin:8px 0 4px;'>定量スナップショット</h4>",
                f"<ul style='margin:0 0 8px 18px;padding:0;'><li>直近終値: {escape(fmt_num(qm.latest_close))}</li><li>直近データ日: {escape(qm.latest_bar_date or 'キャッシュ内にデータなし')}</li><li>データ鮮度: {escape(qm.freshness_label)}</li><li>騰落率: 5D {escape(fmt_pct(qm.ret_5d_pct))}, 20D {escape(fmt_pct(qm.ret_20d_pct))}, 60D {escape(fmt_pct(qm.ret_60d_pct))}</li><li>52週レンジ: 高値 {escape(fmt_num(qm.high_52w))}（高値から {escape(fmt_pct(qm.dist_52w_high_pct))}）, 安値 {escape(fmt_num(qm.low_52w))}（安値から {escape(fmt_pct(qm.dist_52w_low_pct))}）</li><li>出来高: 直近 {escape(fmt_num(qm.latest_volume, 0))}, 20D平均 {escape(fmt_num(qm.avg_volume_20d, 0))}, 出来高倍率 {escape(fmt_num(qm.volume_ratio_20d))}x</li></ul>",
                "<h4 style='margin:8px 0 4px;'>モメンタム根拠</h4>",
                f"<ul style='margin:0 0 8px 18px;padding:0;'><li>{escape(c.short_reason)}</li><li>トレンド継続性は次回データ更新でも確認</li></ul>",
                "<h4 style='margin:8px 0 4px;'>反証・下落リスク</h4>",
                f"<ul style='margin:0 0 8px 18px;padding:0;'><li>{escape(c.counter_evidence)}</li><li>データ本数不足時はトレンド悪化を見落とす可能性があります</li></ul>",
                "<h4 style='margin:8px 0 4px;'>次に確認すること</h4>",
                f"<ul style='margin:0 0 8px 18px;padding:0;'><li>{escape(c.next_checks)}</li><li>深掘り前に直近データ鮮度を再確認</li></ul>",
                "<h4 style='margin:8px 0 4px;'>情報ソース</h4>",
                f"<ul style='margin:0 0 8px 18px;padding:0;'><li>市場データソース: {escape(qm.source)}</li><li>シグナルソース: weekly candidate brief score + momentum labels</li><li>レポート日: {escape(report_date)}</li><li>生成日時: {escape(generated_at)}</li><li>データ不足理由: {escape(qm.missing_reason or 'なし')}</li></ul>",
                "</div>",
            ]
        )
    parts.extend(
        [
            "<h2 style='margin:14px 0 8px;'>補足・安全上の注意</h2>",
            f"<p style='font-size:13px;color:#4b5563;'>{escape(footer)}</p>",
            "</div></body></html>",
        ]
    )
    return "".join(parts)


def _render_copy_markdown_as_simple_html(copy_body: str) -> str:
    blocks: list[str] = []
    for raw in copy_body.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("### "):
            blocks.append(f"<h3>{escape(line[4:])}</h3>")
            continue
        if line.startswith("## "):
            blocks.append(f"<h2>{escape(line[3:])}</h2>")
            continue
        if line.startswith("# "):
            blocks.append(f"<h1>{escape(line[2:])}</h1>")
            continue
        if line.startswith("- "):
            blocks.append(f"<p>- {escape(line[2:])}</p>")
            continue
        blocks.append(f"<p>{escape(line)}</p>")
    return "\n".join(blocks)


def build_weekly_candidate_brief_email_draft(*, report_date: str, copy_body: str) -> WeeklyCandidateBriefEmailDraft:
    """Build Weekly Candidate Brief email body for preview/test send."""

    body_core = copy_body.strip()
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    footer = "観測・深掘り候補の整理です。売買推奨・投資助言・発注指示ではありません。"
    candidates = _parse_top_candidates(body_core)
    zero_reason_notes = _extract_candidate_zero_reason_notes(body_core)
    pipeline_trace_notes = _extract_pipeline_trace_notes(body_core)
    score_veto_notes = _extract_score_veto_summary_notes(body_core)
    monthly_input_notes = _extract_monthly_input_summary_notes(body_core)
    shared_model = extract_weekly_shared_view_model_from_copy_v96(body_core)
    shared_compact_notes = render_weekly_shared_view_model_email_text_v96(shared_model)
    body = _build_rich_text_body(
        report_date=report_date,
        generated_at=generated_at,
        candidates=candidates,
        zero_reason_notes=zero_reason_notes,
        pipeline_trace_notes=pipeline_trace_notes,
        score_veto_notes=score_veto_notes,
        monthly_input_notes=monthly_input_notes,
    )
    if shared_compact_notes and all(note not in body for note in shared_compact_notes):
        body = body.rstrip() + "\n\n" + "\n".join(f"- {x}" for x in shared_compact_notes) + "\n"
    if footer not in body:
        body = f"{body.rstrip()}\n\n---\n{footer}\n"
    html_body = _build_rich_html_body(
        report_date=report_date,
        generated_at=generated_at,
        candidates=candidates,
        footer=footer,
        zero_reason_notes=zero_reason_notes,
        pipeline_trace_notes=pipeline_trace_notes,
        score_veto_notes=score_veto_notes,
        monthly_input_notes=monthly_input_notes,
    )
    return WeeklyCandidateBriefEmailDraft(
        subject=build_weekly_candidate_brief_email_subject(report_date),
        text_body=body,
        html_body=html_body,
    )
