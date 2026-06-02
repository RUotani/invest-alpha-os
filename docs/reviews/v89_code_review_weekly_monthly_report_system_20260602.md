# v89 Code Review — Weekly / Monthly Report System

## 3行サマリー
- 判定: CONDITIONAL PASS。現行の focused / full tests / ruff は通過し、売買指示化につながる重大欠陥は見つからなかった。
- BLOCKER / SHOULD_FIX_BEFORE_MERGE はなし。ただし、月次シートのカスタム入力時のオルタナ差分、copy-to-email parser の静かな取りこぼし、週次とメール間の固定文言重複は次PRで直す価値がある。
- 本レビューは read-only inspection + docs-only report。source変更、workflow変更、live HTTP、cache write、実メール送信、secret表示は未実施。

## 結論

CONDITIONAL PASS

v81〜v88 の Weekly / Monthly Report System は、現状の観測・検証用レポートとしては安全に運用できる水準にある。

一方で、将来の portfolio context 差し替え、copy-ready markdown の構造変更、email preview との文言同期に対しては脆い。次の開発指揮では「機能追加」よりも、構造化入力・単一文言ソース・parser validation を優先すると手戻りが少ない。

## Scope

対象:

- `src/invis_alpha_os/product/weekly_candidate_brief_v0.py`
- `src/invis_alpha_os/reports/weekly_candidate_brief_email.py`
- `src/invis_alpha_os/portfolio/target_allocation_gap_calculator_v82.py`
- `src/invis_alpha_os/portfolio/monthly_decision_sheet_v84.py`
- `tests/test_weekly_candidate_brief_v0.py`
- `tests/test_weekly_candidate_brief_email.py`
- `tests/test_target_allocation_gap_calculator_v82.py`
- `tests/test_monthly_decision_sheet_v84.py`
- `STATE.md`
- `docs/01_development_status.md`
- `docs/decisions/2026-06-02_*.md`
- `docs/reviews/*.md`

基準:

- `HEAD`: `410947ef4ca65f3c3ca27f03915f1207d340d44e`
- `origin/main`: `410947ef4ca65f3c3ca27f03915f1207d340d44e`

## Tests Run

```text
env PYTHONPATH=src .venv/bin/python -m pytest -q \
  tests/test_weekly_candidate_brief_v0.py \
  tests/test_weekly_candidate_brief_email.py \
  tests/test_target_allocation_gap_calculator_v82.py \
  tests/test_monthly_decision_sheet_v84.py

Result: 38 passed in 0.65s
```

```text
env PYTHONPATH=src .venv/bin/python -m ruff check \
  src/invis_alpha_os/product/weekly_candidate_brief_v0.py \
  src/invis_alpha_os/reports/weekly_candidate_brief_email.py \
  src/invis_alpha_os/portfolio/target_allocation_gap_calculator_v82.py \
  src/invis_alpha_os/portfolio/monthly_decision_sheet_v84.py \
  tests/test_weekly_candidate_brief_v0.py \
  tests/test_weekly_candidate_brief_email.py \
  tests/test_target_allocation_gap_calculator_v82.py \
  tests/test_monthly_decision_sheet_v84.py

Result: All checks passed
```

```text
env PYTHONPATH=src .venv/bin/python -m pytest -q \
  -o cache_dir=/private/tmp/invest-alpha-os-code-review-pytest-cache

Result: 1703 passed in 371.87s (0:06:11)
```

## Files Reviewed

### Weekly Candidate Brief

- `weekly_candidate_brief_v0.py` は、候補生成・分類・copy-ready markdown・portfolio制約・cleanup priority・ChatGPTレビュー依頼までを1ファイルで担っている。
- v82 calculator の再利用により、配分ギャップ計算自体は分離されている。
- ただし、表示用日本語文言と分類ロジックが同じモジュールに密集しているため、将来の文言修正時にテストが広く壊れやすい。

### Email Preview

- `weekly_candidate_brief_email.py` は markdown table parser + txt/html rich rendering + portfolio/action checklist を担当している。
- HTML は `ul/li` 中心で、v86a のレビュー方針と整合する。
- 一方で、weekly 本体と同じ portfolio/action 文言を別定数として持っており、差し替え時の同期漏れリスクがある。

### Target Allocation Gap

- v82 calculator は計算ロジックとformat関数が比較的分離され、失敗系の parse test もある。
- `parse_amount_10k_yen` は現在の `万円` 文字列には十分。ただし、portfolio context が数値構造へ移行するなら parser依存を減らす余地がある。

### Monthly Decision Sheet

- v84 monthly sheet は v82 calculator を利用し、Safety note と中立ラベルも反映されている。
- ただし、custom input 時に `temporary_alternatives_10k_yen` と v82用内訳が分離しておらず、将来の差し替えで数値不整合が起きうる。

## Findings

### Critical

なし。

### High

なし。

### Medium

#### M1. Monthly custom input でオルタナ表示値と v82 gap 計算値がズレる可能性

場所:

- `src/invis_alpha_os/portfolio/monthly_decision_sheet_v84.py:35`
- `src/invis_alpha_os/portfolio/monthly_decision_sheet_v84.py:78`
- `src/invis_alpha_os/portfolio/monthly_decision_sheet_v84.py:103`
- `src/invis_alpha_os/portfolio/monthly_decision_sheet_v84.py:158`

内容:

`MonthlyDecisionSheetInputV84` は `temporary_alternatives_10k_yen` を受け取るが、v82 calculator に渡す `CurrentAllocationsV82` では `gold=234.5`, `crypto_high_beta=57.5`, `leverage=10.5` が固定値になっている。

そのため、将来 `build_monthly_decision_sheet_v84_markdown(input_v84=...)` に別ポートフォリオを渡した場合、表示上の暫定オルタナ比率は custom input 由来、配分ギャップの不足額は固定内訳由来になり、同じレポート内で数値が矛盾する可能性がある。

修正案:

- `MonthlyDecisionSheetInputV84` に `gold_10k_yen`, `crypto_high_beta_10k_yen`, `leverage_10k_yen` を持たせる。
- もしくは v82 calculator 側に `temporary_alternatives_10k_yen` を直接受ける alternate constructor を追加する。
- custom input test で `temporary_alternatives_10k_yen != 302.5` のケースを追加する。

#### M2. copy-ready markdown parser が構造変更を静かに取りこぼす

場所:

- `src/invis_alpha_os/reports/weekly_candidate_brief_email.py:22`
- `src/invis_alpha_os/reports/weekly_candidate_brief_email.py:105`
- `src/invis_alpha_os/reports/weekly_candidate_brief_email.py:116`
- `src/invis_alpha_os/reports/weekly_candidate_brief_email.py:121`

内容:

email preview は copy-ready markdown の表を正規表現で再parseしている。期待する6列の表に一致しない行は `continue` されるため、copy-ready 側の列名・列数・区切りが変わった場合、候補が欠落してもエラーにならず、email 側で `注目候補数: 0` に見える可能性がある。

現状テストは英語/日本語テーブルの代表ケースを固定しているが、parser failure が silent である点は運用リスク。

修正案:

- copy-ready の構造を markdown文字列再parseではなく、`WeeklyCandidateBriefV0` または structured digest から直接 email draft を作る。
- 当面の小修正なら、「候補表セクションに非placeholder行があるのに parse 0件」の場合に warning または exit 2 を返す。
- malformed table negative test を追加する。

#### M3. Weekly 本体と email preview の portfolio/action 文言が二重管理

場所:

- `src/invis_alpha_os/product/weekly_candidate_brief_v0.py:70`
- `src/invis_alpha_os/product/weekly_candidate_brief_v0.py:95`
- `src/invis_alpha_os/product/weekly_candidate_brief_v0.py:107`
- `src/invis_alpha_os/reports/weekly_candidate_brief_email.py:50`
- `src/invis_alpha_os/reports/weekly_candidate_brief_email.py:52`
- `src/invis_alpha_os/reports/weekly_candidate_brief_email.py:58`
- `src/invis_alpha_os/reports/weekly_candidate_brief_email.py:64`

内容:

Weekly 本体と email preview がそれぞれ portfolio context / allowed actions / suppressed actions / next checks の定数を持つ。現行値は整合しているが、STATEやportfolio contextが更新されたときに片方だけ古い値を表示するリスクが高い。

修正案:

- weekly側で `WeeklyActionChecklist` のような structured object を生成し、markdown/emailが同じobjectをrenderする。
- 固定文言のsnapshot testに加えて、weekly/emailで重要数値が一致する consistency test を追加する。

### Low

#### L1. Weekly module が候補選定・portfolio制約・copy表示まで抱えて肥大化している

場所:

- `src/invis_alpha_os/product/weekly_candidate_brief_v0.py:755`
- `src/invis_alpha_os/product/weekly_candidate_brief_v0.py:991`
- `src/invis_alpha_os/product/weekly_candidate_brief_v0.py:1135`
- `src/invis_alpha_os/product/weekly_candidate_brief_v0.py:1280`
- `src/invis_alpha_os/product/weekly_candidate_brief_v0.py:1372`

内容:

1ファイル内に scan orchestration、candidate selection、reason generation、portfolio constraint rendering、cleanup score、copy-ready block、full markdown rendering が集中している。現時点では動くが、v90以降で月次/週次/emailが増えるほど変更影響が読みにくくなる。

修正案:

- まずは実装分割より、`WeeklyCandidateBriefViewModel` 的な中間構造を追加してrender関数を薄くする。
- 大規模リファクタは不要。次PRでは `action checklist / no candidate reason / cleanup priority` の構造化だけで十分。

#### L2. tests が文字列存在確認に偏っており、表示リファクタ耐性が低い

場所:

- `tests/test_weekly_candidate_brief_v0.py:119`
- `tests/test_weekly_candidate_brief_email.py:137`
- `tests/test_monthly_decision_sheet_v84.py:23`
- `tests/test_monthly_decision_sheet_v84.py:48`

内容:

Safety wording と必須セクションの固定には有効。ただし、長い substring assert が多いため、文言改善でも広範囲にテスト修正が必要になる。

修正案:

- rendering smoke test は維持する。
- 重要な数値・カテゴリ・禁止語は structured row/list のテストへ寄せる。
- snapshot文字列は「人間向けcopy-readyの最終形」だけに限定する。

#### L3. docs/01_development_status.md の latest verified main が STATE.md より古い

場所:

- `STATE.md:5`
- `docs/01_development_status.md:5`

内容:

`STATE.md` は latest verified main を `a56a189...` としている一方、今回のreview対象 checkout は `410947e...`。`docs/01_development_status.md` も `a56a189...` のまま。v88 refresh後の docs整合は概ね良いが、開発指揮用の「latest main」値は time-dependent なので、次の state refresh で更新確認した方がよい。

修正案:

- v89 report後に `STATE.md` と `docs/01_development_status.md` の latest verified main を更新するか、`current review checkout` と `latest verified main` を別項目に分ける。
- `STATE.md` 変更は承認対象なので、今回は提案に留める。

### Defer

#### D1. Email `--send-test` 正常系は明確にgatedだが、運用上はdry-run主系統を維持

場所:

- `src/invis_alpha_os/cli/main.py:954`
- `src/invis_alpha_os/cli/main.py:1018`
- `src/invis_alpha_os/cli/main.py:1035`
- `src/invis_alpha_os/cli/main.py:1041`
- `tests/test_weekly_candidate_brief_email.py:301`

内容:

`--send-test` は `INVEST_ALPHA_OS_ALLOW_GMAIL_TEST_SEND=1`、recipient、sender、`[TEST]` subject、body prefix、send gate、credential確認を通過した場合のみ送信する。現状のgate設計は妥当。

ただし、project hard boundary では実メール送信は明示承認対象なので、scheduled workflowや通常運用の主経路は引き続き preview生成に限定するべき。

修正案:

- 今すぐ修正不要。
- 将来の運用では `--send-test` を human-only/manual-only とdocsに明記し、CI/scheduledからは呼ばない前提を維持する。

## Architecture / Responsibility Review

良い点:

- v82計算ロジックは `target_allocation_gap_calculator_v82.py` に切り出されている。
- monthly sheet は v82 calculator を再利用しており、数値計算の重複は限定的。
- email HTML は markdown表をそのまま流し込まず、`ul/li` ベースで崩れにくい。

課題:

- weekly module が product logic と rendering を抱えすぎている。
- email renderer が weekly outputを再parseしており、upstream構造に密結合している。
- portfolio/action文言のsingle sourceがない。

## Data Structure Review

良い点:

- `UnifiedCandidate`, `CandidateCard`, `CleanupPriorityRow`, `TargetAllocationGapV82`, `MonthlyDecisionSheetInputV84` など、主要データには dataclass がある。

課題:

- no-candidate reason、action checklist、portfolio constraint がまだ文字列中心。
- email用 `CandidateDigest` は良いが、markdown parser経由で作るため、構造化の効果が限定されている。

## Calculation Logic Review

良い点:

- cash 15/20/30%、equity 49%、individual 10〜15%、bonds/alt 10.5% の計算は focused tests で固定されている。
- full suite でも regressions は出ていない。

課題:

- monthly custom input 時の temporary alternatives 内訳が固定値のまま。
- 現在の portfolio context は v81/v84 固定スナップショットなので、将来の month-end refresh 時は入力構造の見直しが必要。

## Markdown / Email Rendering Review

良い点:

- copy-ready marker があり、ChatGPTへの貼り付け導線が明確。
- no-candidate時の意味、portfolio制約、cleanup priority が週次/email双方に出る。
- HTML は表依存を避けている。

課題:

- copy-ready parser が silent failure しうる。
- copy-ready本文が長く、将来は「ChatGPT貼付用 short」と「full detail」を分ける余地がある。

## Safety Wording Review

良い点:

- `売買指示ではありません`, `観測・検証用`, `売却指示ではなく整理・監視優先度` の明示がある。
- v84b の中立化により、月次テーブルの `買う/売る` 連想は抑制されている。
- veto 0件を「追加可」と誤読させない文言が週次/emailに入っている。

懸念:

- `新規リスク候補` は安全寄りだが、候補があるケースでは `反証確認後に深掘り` が明確に残るよう継続監視する。
- 実メール送信はgatedでも運用承認境界として明示し続ける。

## Test Strategy Review

良い点:

- 285A を含む日本語テーブル parser test がある。
- negative tests と forbidden phrase tests がある。
- full suite 1703件が通っている。

課題:

- malformed copy-ready table の negative test がない。
- monthly custom input の alt mismatch test がない。
- weekly/email consistency test がない。

## Docs / State Review

良い点:

- v84/v84b/v87 の decision doc は安全境界・目的・test が整理されている。
- `STATE.md` と `docs/01_development_status.md` は、Weekly / Monthly の現機能と次の scheduled run 観測を明示している。

課題:

- latest main/hash は time-dependent なので、v89後に更新判断が必要。
- 過去reviewは残っているが、今回のような横断code reviewは `docs/reviews/` に集約するのが妥当。

## Recommended Next PRs

### PR 1: Monthly input consistency hardening

目的:

- `temporary_alternatives_10k_yen` と v82 gap計算の不整合を防ぐ。

内容:

- `MonthlyDecisionSheetInputV84` の alt内訳を構造化。
- custom input negative/regression test 追加。

優先度:

- Medium。次に monthly context refresh を入れる前に対応推奨。

### PR 2: Weekly/email shared view model

目的:

- weekly markdown と email preview の文言・数値ズレを防ぐ。

内容:

- action checklist / portfolio constraint / no-candidate reason を shared structured object 化。
- weekly/email consistency test 追加。

優先度:

- Medium。大きなリファクタではなく、重複定数の削減に絞る。

### PR 3: Copy parser validation

目的:

- copy-ready構造変更時に email候補数が静かに0件化するのを防ぐ。

内容:

- malformed table negative test。
- parseできない候補行がある場合の warning/exit policy。

優先度:

- Medium。scheduled artifact review前後で対応検討。

## Safety Summary

実施:

- read-only code inspection
- focused pytest
- full pytest
- ruff check
- docs-only review report 追加

未実施:

- source実装変更
- workflow変更
- `.github/workflows/*` 変更
- provider live HTTP
- market-data live fetch
- cache write
- actual refresh/import
- broker API
- raw broker export parsing
- raw broker data persistence
- env/secret display
- dependency / pyproject / Makefile changes
- trading action
- order placement
- 自動売買
- 実メール送信

## Final Verdict

CONDITIONAL PASS

このBOTの v81〜v88 Weekly / Monthly Report System は、現行main上ではテスト・lint・安全文言の観点で実運用観測に進める。ただし、次の開発指揮では新機能追加より、以下3点を優先するのが合理的。

1. monthly custom input と v82 alt gap の整合化
2. weekly/email の shared view model 化
3. copy-ready parser の silent failure 防止

## 次にChatGPTへ貼る要約

```markdown
# v89 Code Review Summary — Weekly / Monthly Report System

判定: CONDITIONAL PASS

Tests:
- focused: 38 passed
- ruff: All checks passed
- full suite: 1703 passed

BLOCKER / SHOULD_FIX_BEFORE_MERGE:
- なし

Medium:
- Monthly custom inputで `temporary_alternatives_10k_yen` とv82 gap計算のalt内訳がズレる可能性あり。次のmonthly context refresh前に修正推奨。
- email previewがcopy-ready markdown表をregex再parseしており、表構造変更時に候補を静かに0件化する可能性あり。parser validationまたはshared view model化推奨。
- Weekly本体とemail previewでportfolio/action文言が二重管理。portfolio context更新時の同期漏れリスクあり。

Low / Defer:
- weekly moduleが候補選定・portfolio制約・copy renderingまで抱えて肥大化。
- testsは文字列存在確認が多く、表示リファクタに弱い。
- `--send-test` はgatedで妥当だが、通常運用はdry-run preview主系統を維持。

推奨Next PR:
1. Monthly input consistency hardening
2. Weekly/email shared view model
3. Copy parser validation

Safety:
- docs-only review
- source変更なし
- workflow変更なし
- live HTTP/cache write/actual import/broker API/secret表示/実メール送信なし
```
