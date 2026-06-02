# v80 Weekly Report Content Quality Review / UX Improvement Plan

## 結論

v79 artifact の週次レポートは、配信・artifact・copy-ready 生成物としては成立しているが、投資判断支援OSとしてはまだ不十分。現状は「候補生成の死活監視」には使えるが、「今週何を確認し、何を避け、どの制約下で判断するか」を導くレポートには届いていない。

次PRでは、実装範囲を小さく保ちつつ、候補ゼロ時の説明、portfolio-aware な行動制御、買い/待ち/避ける/cleanup の分類、ChatGPTに貼れるレビュー入力の改善を優先する。

## 対象artifact

| 項目 | 内容 |
|---|---|
| workflow | `weekly-candidate-brief` |
| run ID | `26788988868` |
| event | `workflow_dispatch` |
| conclusion | `success` |
| head SHA | `f4b74c4383afb041d692c9c0b231695ebb5ecc4b` |
| artifact | `weekly-candidate-brief` |
| artifact ID | `7345652882` |
| local review path | `/private/tmp/invest-alpha-os-v79-artifact` |

## 対象ファイル

| ファイル | レビュー扱い |
|---|---|
| `weekly_candidate_brief_v0_1.md` | 主対象 |
| `weekly_candidate_brief_copy.md` | 主対象 |
| `email_preview.txt` | 主対象 |
| `email_preview.html` | 主対象 |
| `email_preview.eml` | 存在・受信経路確認 |
| `status.json` | 生成状態確認 |
| `email_raw.b64url.txt` | 存在確認のみ。本文表示なし |

## 総合評価

現状の週次レポートは、生成成功を確認できる運用artifactとしては合格。ただし、投資判断支援OSの主画面としては、判断材料・portfolio制約・次アクションの接続が弱い。

特に、今回のartifactでは上位候補が0件であり、copy-ready sectionにも「なぜ0件か」「次に何を見るか」「買わない理由」が十分に出ていない。これは安全上は悪くないが、ユーザー体験としては「空のレポート」に見える。

## 良い点

- workflow_dispatch から artifact までの経路は成立している。
- レポート冒頭に observation-only / not trading advice の境界が明記されている。
- copy-ready section が `<<< COPY FROM HERE >>>` から `<<< COPY TO HERE >>>` で分離されている。
- データ不足候補には反証と次確認があり、買い煽りを避ける方向になっている。
- email preview は最低限の要約、候補数、安全注意を含む。

## 不足点

- 冒頭30秒で「今週の判断」が分からない。
- 候補0件の理由がcopy-ready sectionに出ておらず、失敗なのか正常な見送りなのか分かりにくい。
- 現金11.7%、個別株19.6%、株式系67.8%というportfolio制約と接続していない。
- Buy / Watch / Avoid / Cleanup の分類がなく、行動制御に使いにくい。
- 数値根拠がほぼない。価格、変化率、出来高、52週高値、移動平均、ボラティリティが見えない。
- email HTML 内でMarkdown表が段落表示になっており、モバイル表示で読みやすい表になっていない。
- ChatGPTへ貼ると、候補ゼロの背景説明が不足し、追加説明が必要になる。

## 機能別レビュー

### 1. Executive Summary

判定: 不十分。

現状のcopy-ready sectionは「上位5件なし」と「見方」だけで、ユーザーが次に取るべき行動を判断しにくい。週次レポートの冒頭には、以下の3点を固定で出すべき。

- 今週の結論: 例 `新規買い候補なし。データ品質不足のため、今週はcleanup / data readiness確認を優先。`
- 今週やること: 最大3件
- 今週やらないこと: 例 `候補ゼロを理由に無理な新規買いをしない`

### 2. Portfolio Connection

判定: 不十分。

v78で月次portfolio contextが整ったにもかかわらず、週次レポート側にはまだ接続されていない。2026年5月末修正版では、現金11.7%、個別株19.6%、株式系67.8%であり、新規買い候補探索よりも、現金回復、個別株圧縮、cleanup優先が自然な文脈。

週次レポートには、少なくとも以下の表示が必要。

- cash pressure: 現金比率が目標15-20%に対して低いか
- individual stock pressure: 個別株比率が10-15%目標に対して高いか
- action bias: 新規買い / watch / cleanup / no action のどれを優先する週か

### 3. Candidate Classification

判定: 不十分。

現状は「Top 5」「急騰」「押し目」「過熱・避ける」「データ不足」に分かれているが、portfolio action としての分類ではない。投資判断支援OSとしては、以下の分類が必要。

- Buy candidate: 新規検討に値するが、実行指示ではない
- Watch candidate: 条件待ち
- Avoid / Veto candidate: 今は触らない
- Cleanup candidate: 既存保有の整理・縮小候補
- Data blocked: データ不足で判断不能

今回artifactではAAPL、AMZN、COINが「データ不足・要注意」に出ているが、これは買い候補ではないことがcopy-ready sectionに出ていない。

### 4. Quantitative Evidence

判定: 実用前に近い。

今回のレポートには、銘柄別の価格、変化率、出来高、移動平均、52週高値、ボラティリティ、valuationが出ていない。`discovery_score` も0であり、なぜその銘柄が出たのかを定量的に検証できない。

ただし、この不足はcache writeやprovider live fetchを実行して解決するべきではない。まずは既存local cache / redacted context / dry-run metricsの範囲で、以下のような「数値がない理由」を明示するのが安全。

- data_quality_status
- available_window_days
- missing_metric_reason
- candidate_score_components

### 5. Risk / Veto / Safety

判定: 最低限は合格。

売買推奨ではない注意書きは明確で、データ不足の反証もある。危険な買い煽りは見られない。

一方で、NISA売却不可、AI集中ルール、現金比率低下、個別株過多、高ボラ/レバ商品のcleanup優先といった、ユーザー固有のrisk/vetoが週次レポートに接続されていない。

### 6. UX / Readability

判定: 最低限。

Markdown本文は短く読めるが、候補ゼロ時には短すぎて判断材料がない。email previewはスマホでも読めるが、HTMLではMarkdown表が普通の段落として出ており、視認性が弱い。

改善するなら、長い表を増やすより、以下の順序がよい。

1. 3行結論
2. 今週のaction bias
3. 候補分類別の短いカード
4. データ不足理由
5. ChatGPT貼り付け用ブロック

### 7. ChatGPT Review Readiness

判定: 弱い。

copy-ready blockはあるが、ChatGPTに貼るための前提が足りない。最低限、以下が必要。

- report_date
- run type: scheduled / manual dispatch
- candidate count
- no-candidate reason
- portfolio constraints
- explicit ask: `この週次レポートを、買い煽りを避けてcleanup/risk-control優先でレビューしてください`

### 8. Email / Mobile Readiness

判定: 最低限。

email_preview.txtは短く、スマホで読める。ただし「no candidates in copy body」は機械的で、ユーザー向け文言として弱い。email_preview.htmlは表がHTML table化されておらず、Markdownのパイプ表が段落として表示される。

## 十分 / 不十分 判定表

| 評価領域 | スコア / 5 | 判定 | コメント |
|---|---:|---|---|
| Executive Summary | 2 | 不十分 | 候補0件の結論と次アクションが弱い |
| Portfolio Connection | 1 | 不十分 | v78の月次portfolio制約と未接続 |
| Candidate Classification | 2 | 不十分 | data blockedはあるがBuy/Watch/Avoid/Cleanupではない |
| Quantitative Evidence | 1 | 実用前 | 価格・変化率・出来高・期間・score内訳がない |
| Risk / Veto / Safety | 3 | 最低限 | 売買推奨回避は良いが、固有veto未接続 |
| UX / Readability | 2 | 不十分 | 短いが、空レポートに見えやすい |
| ChatGPT Review Readiness | 2 | 不十分 | copy blockはあるが前提不足 |
| Email / Mobile Readiness | 2 | 不十分 | txtは読めるがhtml表現が弱い |
| Overall | 2 | 不十分 | 生成物としては合格、投資判断支援OSとしては改善必須 |

## 優先改善テーマ

1. 候補ゼロ時UXの改善
   - 空欄ではなく、`今週は新規買い候補なし / 理由 / 次確認 / 禁止行動` を出す。
2. Portfolio-aware action bias
   - 現金11.7%、個別株19.6%、株式系67.8%を踏まえ、新規買いよりcleanup/risk-controlを優先する文脈を出す。
3. Candidate classificationの再設計
   - Buy / Watch / Avoid / Cleanup / Data blocked に分ける。
4. Quant evidence scaffolding
   - live fetchなしで、既存データから出せるmetricと出せないmetricを明示する。
5. ChatGPT貼り付け用contextの改善
   - report summary、portfolio constraints、review askをcopy blockへ入れる。

## 次PR候補

| 優先 | 候補 | 判断 | 理由 |
|---:|---|---|---|
| 1 | v81 Weekly Report UX Upgrade Pack | 最優先 | 小さく実装でき、候補ゼロ時の誤読を減らす |
| 2 | v85 Portfolio-Aware Weekly Action Checklist | 高 | 毎週の行動制御に直結する |
| 3 | v83 Cleanup Priority Scoring Pack | 高 | 現在のportfolio制約では新規買いよりcleanupが重要 |
| 4 | v82 Target Allocation Gap Calculator | 中 | 月次portfolioと週次行動を接続する基盤 |
| 5 | v84 Monthly Decision Sheet Pack | 中 | 月次レビュー向けで、週次UX改善後がよい |

## v81 Implementation Plan案

v81は大きく作り替えず、週次レポートgeneratorの表示改善に限定する。

Scope:

- no-candidate summary blockを追加
- copy-ready sectionにcoverage noteを昇格
- `今週やること / やらないこと` を最大3件ずつ追加
- run typeとartifact statusを表示
- email previewのno-candidate文言を自然な日本語へ変更
- Markdown表をHTML previewで崩さないため、候補0件時は表を使わず短い箇条書きにする

Out of scope:

- workflow変更
- provider live fetch
- cache write
- actual import
- broker/export parsing
- trading action
- 価格帯つき売買推奨

Suggested tests:

- candidate count 0 のcopy-ready blockに no-candidate reason が入る
- coverage note がcopy-ready sectionに入る
- email_preview.txtで `no candidates in copy body` が出ない
- HTML previewでMarkdownパイプ表が段落表示されない
- safety disclaimerが残る

## Safety Summary

- provider live HTTP: not used
- market-data live fetch: not used
- cache write: not used
- cache directory creation: not used
- actual import: not used
- broker API: not used
- raw broker export parsing: not used
- env/secret display: not used
- workflow change: not used
- trading action: not used
- GitHub repo/artifact operation: not newly used in v80; existing v79 artifact under `/private/tmp` was inspected
- This review did not use market/provider live HTTP

## 次にChatGPTへ貼る要約

v80でv79 weekly_candidate_brief artifactをレビューした。workflow/artifact/email previewとしては成功しているが、投資判断支援OSとしてはOverall 2/5で不十分。主因は、候補0件時に理由と次アクションがcopy-ready sectionへ出ないこと、v78のportfolio制約（現金11.7%、個別株19.6%、株式系67.8%）と接続していないこと、Buy/Watch/Avoid/Cleanup分類や定量根拠が不足していること。次PRはv81 Weekly Report UX Upgrade Packを最優先とし、no-candidate summary、coverage note昇格、今週やる/やらない、email preview文言改善、ChatGPT貼り付け用context改善をsource-onlyで実装するのがよい。
