# Claude Review Request — invest-alpha-os Weekly Report v1.6.1

作成日: 2026-06-06  
対象: v1.6.1 email top summary fix（Claude再レビュー前）

## Context

- **Previous problem**: v1.6 trial Gmail（message_id `19e9b98cdda38b5d`）の snippet に `最重要候補 285A` が残存。v1.6設計（285A = Overheated / Do Not Chase / Theme Proxy）と矛盾。
- **v1.6 / v1.6.1 fixes**:
  - freshness gate（fresh / stale_warning / expired）
  - overheated leaders / Do Not Chase 振り分け
  - render bucket 整合（`WeeklyReportRenderModel`）
  - mobile 縦カード
  - 内部用語の下部移動
  - **v1.6.1**: Gmail/Markdown/User Summary 上部要約から旧 Top Pick 表現を除去

## v1.6.1 Trial Send

| 項目 | 値 |
|---|---|
| message_id | `19e9ba84a9f1026d` |
| trial_root | `reports-private/trial_send/weekly_v1_6_1_2026-06-06/` |
| transport | gmail_oauth |

## Review Goals

Claude に以下を評価してほしい:

1. レポートは investable early candidate 0件を正直に示しているか？
2. 285A は overheated / theme proxy として適切に分離されているか？
3. stale 候補は鮮度ゲートで明確に止まっているか？
4. Gmail / mobile レイアウトは理解しやすいか？
5. 誤解を招く用語（最重要候補、Top Pick 等）はまだ残っていないか？
6. 次に何をすべきか判断に役立つか？
7. v1.7 前に改善すべき点は何か？

## Output Requested from Claude

- Critical issues
- UI issues
- Content trust issues
- Algorithm / reporting issues
- Next implementation tasks
- **Pass/fail judgment for v1.6.1**

---

## Embedded: weekly_report copy block（v1.6.1 上部）

```markdown
# 週次候補ブリーフ — 2026-06-06

## 今週の結論（3行）

- 状態: 初動候補は0件。過熱銘柄で無理に埋めません。
- 最大リスク: 現金不足 / 個別株多め / 急騰後の過熱
- 今週やる/やらない: やる: guardrailとデータ鮮度確認 / やらない: 根拠不足の新規追加
- 集計: 初動・深掘り 0件 / 過熱代表 1件 / 鮮度不足 5件 / 深掘り優先度カウント 0件
- これは売買指示ではありません。

## 初動・深掘り候補

初動候補は0件。過熱銘柄で無理に埋めません。

## 過熱代表 / Do Not Chase

[テーマ代表（追いかけ禁止）] 285A（285A キオクシア） JP
扱い: 追いかけ禁止 / 周辺・出遅れ候補を探す
```

---

## Embedded: weekly_report_user_summary_v1_6_1.md

```markdown
# Weekly Report One-Page Summary

## 1. 今週の結論

初動候補は0件。過熱銘柄で無理に埋めません。これは売買指示ではありません。

## 2. 候補の扱い

| 区分 | 件数 | 代表 | 扱い |
|---|---:|---|---|
| 投資妙味候補（初動・深掘り） | 0 | — | 該当なし |
| 過熱代表 / Do Not Chase | 1 | 285A キオクシア | 追いかけ禁止 / 周辺・出遅れ候補を探す |
| データ鮮度不足 | 5 | 6857 ほか | 深掘り・監視候補に昇格させない |
```

---

## Embedded: Gmail email top summary（v1.6.1 修正後・readable excerpt）

```text
今週の結論（上部要約）
- 今週の状態: 初動候補は0件。過熱銘柄で無理に埋めません。
- 投資妙味候補: 0件
- 過熱代表: 285A キオクシア（追いかけ禁止）
- 最大リスク: 現金不足 / 個別株多め / 急騰後の過熱
- 今週やる/やらない: やる: guardrailとデータ鮮度確認 / やらない: 根拠不足の新規追加

（旧 v1.6 問題: ここに「最重要候補 285A」が出ていた → v1.6.1 で除去済み）
```

---

## Full Artifact Paths

- `reports-private/sample_outputs/weekly_report_v1_6_1_sample.md`
- `reports-private/sample_outputs/weekly_email_preview_v1_6_1.html`
- `reports-private/sample_outputs/weekly_report_user_summary_v1_6_1.md`
- `reports-private/trial_send/weekly_v1_6_1_2026-06-06/send_result.md`
