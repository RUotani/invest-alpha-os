# R6.19-A — Gmail delivery and display names

**日付**: 2026-05-20 · **性質**: opt-in operator email · **default enablement 未変更**

---

## 1. Purpose

- レポートに **コード + 短縮名**（`5802 住友電工` · `MSFT Microsoft`）を表示
- R6.18-U operator bundle から **日次観測メール**を生成（dry-run 既定）
- **Gmail API 送信**は明示ゲートのみ（`CONFIRM_GMAIL_SEND=YES` 等）

---

## 2. Display names

- 設定: `config/symbol_display_names.yaml`
- ヘルパー: `reports/symbol_display_names.py`
- JP signals 表: `Code / Name` 列
- US cache preview: `symbol / name` 列
- 未知シンボルは **コードのみ**にフォールバック

---

## 3. Daily usage email flow

1. R6.18-U と同様に `outputs/operator/daily_usage/YYYY-MM-DD/` を用意
2. dry-run でプレビュー生成:

```bash
.venv/bin/python -m invis_alpha_os.cli.main daily-email \
  --bundle-dir outputs/operator/daily_usage/2026-05-20 \
  --dry-run
```

3. 出力: `bundle/email/email_preview.{eml,txt,html}` · `email_raw.b64url.txt`

---

## 4. Gmail API setup（送信時のみ）

Optional packages（送信時）:

```bash
pip install -e ".[gmail]"
# または
pip install google-api-python-client google-auth-oauthlib google-auth-httplib2
```

OAuth scope: `https://www.googleapis.com/auth/gmail.send`

### 初回トークン（R6.19-D）

`gmail_credentials.json` のみあれば **`daily-email --send` 初回**でブラウザ OAuth が開き、`GMAIL_TOKEN_FILE`（既定 `~/.config/invest-alpha-os/gmail_token.json`）に保存される。トークン期限切れ時は refresh token があれば自動更新。

ローカル（**コミット禁止**）:

- `GMAIL_CREDENTIALS_FILE` — OAuth client JSON パス
- `GMAIL_TOKEN_FILE` — 既定 `~/.config/invest-alpha-os/gmail_token.json`

---

## 5. Gated send command

```bash
CONFIRM_GMAIL_SEND=YES \
GMAIL_REPORT_TO="your.address@gmail.com" \
GMAIL_REPORT_ALLOWLIST="your.address@gmail.com" \
GMAIL_CREDENTIALS_FILE="$HOME/.config/invest-alpha-os/gmail_credentials.json" \
GMAIL_TOKEN_FILE="$HOME/.config/invest-alpha-os/gmail_token.json" \
.venv/bin/python -m invis_alpha_os.cli.main daily-email \
  --bundle-dir outputs/operator/daily_usage/2026-05-20 \
  --send
```

---

## 6. Safety gates

| Gate | 必須 |
|---|---|
| `--send` | 送信モード |
| `CONFIRM_GMAIL_SEND=YES` | はい |
| `GMAIL_REPORT_TO` | はい |
| `GMAIL_REPORT_ALLOWLIST` または `GMAIL_SELF_EMAIL` | 受信者制限 |
| `GMAIL_CREDENTIALS_FILE` 存在 | はい（token は初回 send で作成可） |

dry-run は **Gmail API を呼ばない**（OAuth フローなし）。

---

## 7. What is not allowed

- default daily/signals preview enablement
- 市場 live HTTP / cache write
- 資格情報・トークンのコミット
- 無制限送信
- 売買推奨メール

---

## 8. Troubleshooting

| 症状 | 対処 |
|---|---|
| `Gmail API packages not installed` | optional deps をインストール |
| `CONFIRM_GMAIL_SEND` | `YES` を設定 |
| `recipient not in allowlist` | `GMAIL_REPORT_ALLOWLIST` に To を追加 |
| dry-run のみで十分 | `--dry-run`（既定）のまま `.eml` を確認 |

---

## 9. Future automation

- cron/launchd は **別承認**
- GitHub Actions + secrets は **別承認**
- まずは手動 daily-email dry-run → 必要時のみ gated send
