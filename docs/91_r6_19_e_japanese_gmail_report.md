# R6.19-E — Japanese Daily Gmail Report

**日付**: 2026-05-20 · **性質**: `daily-email` 日本語レンダリング

---

## 1. Purpose

`daily-email` の件名・本文・表見出しを日本語化し、観測専用の免責を維持したまま Gmail 配信品質を改善する。

---

## 2. Implementation

| 領域 | 変更 |
|---|---|
| `reports/daily_email.py` | 日本語件名 `投資観測レポート` · セクション（サマリー / 日本株モメンタム / 米国株プレビュー / 注意 / 生成情報）· 表ヘッダ翻訳 · 鮮度表記 |
| `tests/test_daily_email_delivery.py` | 日本語件名・本文のアサーション |

**方針**: バンドル内 Markdown を構造化してラップ。売買推奨・発注・配分の文言は追加しない。

---

## 3. Verification

| チェック | 結果 |
|---|---|
| dry-run | pass（`投資観測レポート` · 日本語セクション） |
| `tests/test_daily_email_delivery.py` | **13 passed** |
| gated `--send` | pass（`CONFIRM_GMAIL_SEND=YES`） |
| ユーザー目視 | 日本語 Gmail 受信を確認済み |

---

## 4. Safety

- credentials / token / `.env`: **未出力・未コミット**
- market live HTTP / cache write: **なし**
- daily / signals default: **変更なし**
- 観測のみ · 売買推奨なし

---

## 5. Related

- [docs/80](./80_r6_19_a_gmail_delivery_and_display_names.md) · [docs/89](./89_r6_19_d_gmail_oauth_token_bootstrap.md) · [docs/90](./90_r6_19_f_launchd_0700_gmail_setup.md)（07:00 launchd · E マージ後に日本語恒久化）
