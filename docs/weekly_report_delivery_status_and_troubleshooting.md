# Weekly Report Delivery Status / Gmail Troubleshooting

## 3行サマリー

- 配信状態は `generated / preview_created / sent / delivered / blocked / failed` の6段階で記録する。
- `sent` は送信処理の受付成功、`delivered` は受信側で到達確認済みを意味し、同一ではない。
- v1.2 weekly report は候補より先に portfolio guardrail を読み、Gmail障害時も売買判断を急がない。

## Delivery Status Taxonomy

| Status | 意味 | 必要な証拠 | 次アクション |
|---|---|---|---|
| `generated` | weekly report本文が生成された | report本文またはmanifest | preview生成へ進む |
| `preview_created` | email previewが生成されたが実送信は未確認 | `email_preview.txt` / `email_preview.html` またはruntime `dry_run` | 内容・宛先・guardrailを確認 |
| `sent` | SMTP/Gmail APIが送信処理を受け付けた | runtime `sent`、transport、redacted recipient、可能ならmessage id | 受信側到達を確認 |
| `delivered` | 受信側でメール到達を確認した | inbox側確認、または同等のdelivery evidence | report内容をレビュー |
| `blocked` | gate・設定・宛先検証で送信前に停止した | runtime `blocked` とreason/missing key名 | secret値を表示せず設定を確認 |
| `failed` | 生成または送信処理を試行したが失敗した | runtime `failed` と安全なreason | preview正本を読み、原因を切り分ける |

### Runtime Status Mapping

既存runtimeの状態は次のように正規taxonomyへ対応付ける。runtime実装はこのdocs/tests補助タスクでは変更しない。

| Runtime / Evidence | Normalized Status |
|---|---|
| report本文またはgeneration manifestのみ | `generated` |
| `email_delivery_status=dry_run` またはpreview artifactあり | `preview_created` |
| `email_delivery_status=sent` | `sent` |
| inbox側到達確認あり | `delivered` |
| `email_delivery_status=blocked` | `blocked` |
| `email_delivery_status=failed` | `failed` |

**禁止判断:** `sent` やmessage idだけを根拠に `delivered` と記録しない。

## Guardrail-First Reading Order

Gmailで届いたv1.2 weekly reportは、個別候補より先にportfolio guardrailを読む。

1. Executive Summaryで「即時行動ではなく深掘り / 監視 / 見送り」を確認する。
2. Portfolio Guardrailsで現金比率、個別株比率、株式系合計を確認する。
3. Candidate Comparisonで候補理由と反証を比較する。
4. Deep Dive CardsとIf / Then Decision Rulesで次の調査を決める。

現金比率が15%未満、個別株比率が目安超過、またはveto継続の場合、候補の魅力よりguardrailを優先する。これは売買指示ではない。

## Gmail Delivery Troubleshooting

### `generated`

- report本文とmanifestの存在を確認する。
- previewが無い場合は、実送信ではなくpreview生成経路を先に確認する。
- report内容の上部にExecutive SummaryとPortfolio Guardrailsがあるか確認する。

### `preview_created`

- `email_preview.txt` または `email_preview.html` を正本として読む。
- runtime `dry_run` は「送信済み」ではない。
- 宛先はredacted表示だけを確認し、完全なメールアドレスをログへ出さない。

### `sent`

- transportが `smtp` または `gmail_oauth` のどちらか確認する。
- message idがある場合も、受信側確認までは `delivered` にしない。
- 迷惑メール、スレッド分類、受信時刻を受信側で確認する。

### `delivered`

- inbox側で件名、report date、本文のguardrail-first構造を確認する。
- 到達確認はsecret、OAuth token、raw credentialの表示を必要としない。
- 内容が古い場合はdelivery成功とreport freshness問題を分離する。

### `blocked`

- `reason` と `missing` のキー名だけを確認する。
- secret値、env値、OAuth token、credential JSON本文を表示しない。
- 典型例: send gate未設定、recipient未設定、credential不在、email address不正。

### `failed`

- `reason`、transport、redacted recipientだけで切り分ける。
- previewが読める場合、配信失敗とreport生成失敗を分離する。
- retryや実送信は別承認・別タスクとして扱う。

## Secret Non-Display Contract

- 表示可: env key名、missing key名、redacted recipient、safe reason、transport、message id。
- 表示禁止: password、OAuth token、credential JSON本文、完全なrecipient、raw SMTP/Gmail response。
- docs、tests、ログ、PR本文へplaceholder以外のsecret値を記載しない。

## Scope Boundary

このdocs/tests補助タスクは、workflow、`reports-private/trial_send`、Gmail実送信、launchd、runtime source実装を変更しない。
