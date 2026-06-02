# v82a Manual Trial Allocation Gap Display Review

## 結論
PASS

## Run / Artifact
- workflow: `weekly_candidate_brief.yml`
- run id: `26803119044`
- event: `workflow_dispatch`（manual trial 1回）
- run URL: https://github.com/RUotani/invest-alpha-os/actions/runs/26803119044
- conclusion: `success`
- artifact: `weekly-candidate-brief`
- local review path: `/private/tmp/invest-alpha-os-v82a-manual-trial-artifact`

## Files Reviewed
- `weekly_candidate_brief_v0_1.md`
- `weekly_candidate_brief_copy.md`
- `email_preview.txt`
- `email_preview.html`
- `email_preview.eml`
- `status.json`

## Required Display Checks (v82)
- `目標配分ギャップ（v82）` セクション: **PASS**
  - `weekly_candidate_brief_v0_1.md` / `weekly_candidate_brief_copy.md` で確認
- 現金 15% / 20% / 30% への不足額表示: **PASS**
  - `不足 790.2万円（最低15%まで +141.0万円 / 20%まで +357.4万円）`
- 株式系 67.8% vs 49.0% overweight: **PASS**
  - `上回り +813.8万円`
- 個別株 19.6% vs 10〜15% band above band: **PASS**
  - `上限15%超過 4.6%（+197.1万円）`
- 債券 13.5% vs 10.5% / 暫定オルタナ 7.0% vs 10.5%: **PASS**
  - 債券: `上回り +128.3万円`
  - オルタナ: `不足 151.9万円`
- email preview 3行要約: **PASS**
  - `email_preview.txt` と `email_preview.html` に 3行とも出力

## Safety / Messaging Review
- 売買指示・注文誘導に見えないか: **PASS**
  - `この差分は売買指示ではなく...` を確認
  - `売買推奨・投資助言・発注指示ではありません` を確認
- 実メール送信: **未実施**
  - review対象は preview artifact のみ（read-only）

## UI / Readability Review
- Markdown 側の可読性: **PASS**
  - 追加セクションは短い箇条書き 6行で、既存 copy-ready 構造を壊していない
- Email（txt/html）可読性: **PASS**
  - 3行要約は checklist 先頭に配置され、1画面目で把握可能
  - HTML は `ul/li` で表示され、表崩れは見当たらない
- スマホ/メール負荷: **概ね良好**
  - 3行はやや長文だが、条書きとしては許容範囲

## status.json Check
- `status`: `weekly_candidate_brief_generated`（成功系）
- `completed_at`: `2026-06-02T06:41:12Z`（run時刻と整合）
- date/path: `2026-06-02` artifact と整合

## Gaps / Minor Notes
- 3行要約は情報量が高く、モバイルでは折り返し行数が増える可能性あり（機能的問題はなし）
- 現時点では PASS 判定を維持。必要なら文言を次PRで軽量化可能

## Safety Summary
- 実施内容は workflow_dispatch 1回、artifact download、read-only review、docs 追加のみ
- 禁止事項（workflow変更、provider live HTTP、market-data live fetch、cache write、actual import、broker API、raw broker export parsing、env/secret表示、dependency/pyproject/Makefile変更、trading action、実メール送信）は未実行

## 判定
PASS

## Next Actions
- 次の scheduled weekly run（v86系観測）でも同じ v82 表示が出ることを確認する
- 必要なら email 3行要約の文言圧縮を検討（NICE_TO_HAVE）

