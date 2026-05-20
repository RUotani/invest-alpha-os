# R6.19-G — Japanese Gmail Narrative + No Markdown Attachments

**日付**: 2026-05-20 · **main 起点**: `393c509`+

---

## 1. Purpose

日本語 Gmail 日次レポートの品質改善:

1. **`.md` 添付を廃止**（本文 HTML/テキストのみ）
2. **ナラティブ本文**（注目ポイント · 銘柄別コメント · 次に確認すること）
3. gated サンプル送信で受信確認

---

## 2. Changes

| ファイル | 内容 |
|---|---|
| `reports/daily_email.py` | 表パース · 今日の注目 · 銘柄別コメント · HTML 構造化 |
| `cli/main.py` | `attachments=None`（送信/dry-run 共通） |

---

## 3. Verification

| チェック | 結果 |
|---|---|
| dry-run | 日本語セクション + ナラティブ |
| `tests/test_daily_email_delivery.py` | pass（添付なし含む） |
| gated `--send` | ローカル実行 |
| 添付 | `.md` なし |

---

## 4. Safety

- secrets/token: 未出力・未コミット
- 売買推奨・発注文言: なし
- live HTTP/cache write: なし
- default 変更: なし
