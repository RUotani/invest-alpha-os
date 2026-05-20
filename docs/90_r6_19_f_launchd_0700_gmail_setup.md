# R6.19-F — Daily Gmail 07:00 launchd Setup

**日付**: 2026-05-20 · **性質**: ローカル ops 記録（LaunchAgent は **未コミット**）

---

## 1. Purpose

日本語の日次観測 Gmail レポートを、毎朝 **07:00（Mac ローカル時刻）** に `launchd` から gated 送信する。

---

## 2. Prerequisites（確認済み）

| 項目 | 状態 |
|---|---|
| `~/.config/invest-alpha-os/daily_gmail.env` | あり |
| `gmail_credentials.json` | あり |
| `gmail_token.json` | あり（R6.19-D） |
| `CONFIRM_GMAIL_SEND=YES` | あり |
| `GMAIL_REPORT_TO` 等 | 設定済み |
| 日本語レポート受信（手動送信） | ユーザー確認済み |

**注意**: 日本語メール本文は **R6.19-E**（`daily_email.py`）の反映が必要。`main` に未マージの間は 07:00 送信が英語ラッパーのままになる可能性あり。

---

## 3. launchd インストール

テンプレート: `ops/launchd/com.invest-alpha-os.daily-gmail-report.plist.template`

| 項目 | 値 |
|---|---|
| Label | `com.invest-alpha-os.daily-gmail-report` |
| Plist（ローカル） | `~/Library/LaunchAgents/com.invest-alpha-os.daily-gmail-report.plist` |
| 実行 | `/bin/zsh` → `scripts/run_daily_gmail_report.sh --send` |
| 時刻 | `StartCalendarInterval` **Hour=7 Minute=0**（ローカル） |
| `RunAtLoad` | なし（即時送信しない） |
| env | スクリプト内で `daily_gmail.env` を source |

インストール手順（再現）: [docs/81](./81_r6_19_b_daily_0700_gmail_delivery_runbook.md) §7

```bash
mkdir -p "$HOME/Library/LaunchAgents" "$HOME/Library/Logs/invest-alpha-os"
sed -e "s#__REPO_ROOT__#$(pwd)#g" \
    -e "s#__LOG_DIR__#$HOME/Library/Logs/invest-alpha-os#g" \
  ops/launchd/com.invest-alpha-os.daily-gmail-report.plist.template \
  > "$HOME/Library/LaunchAgents/com.invest-alpha-os.daily-gmail-report.plist"
launchctl bootout "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.invest-alpha-os.daily-gmail-report.plist" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.invest-alpha-os.daily-gmail-report.plist"
launchctl enable "gui/$(id -u)/com.invest-alpha-os.daily-gmail-report"
```

---

## 4. Verification（2026-05-20）

| チェック | 結果 |
|---|---|
| `plutil -lint` | OK |
| `launchctl print gui/.../com.invest-alpha-os.daily-gmail-report` | loaded · Hour=7 Minute=0 |
| `scripts/run_daily_gmail_report.sh --dry-run` | OK |
| プレビュー日本語（`投資観測レポート` 等） | OK（R6.19-E コード使用時） |
| 本日 `email_sent.json` | **なし**（手動送信は重複回避のため未実施） |
| 次回自然送信 | **翌 07:00** |

---

## 5. Logs

| ログ | パス |
|---|---|
| launchd stdout | `~/Library/Logs/invest-alpha-os/launchd_daily_gmail_report.out.log` |
| launchd stderr | `~/Library/Logs/invest-alpha-os/launchd_daily_gmail_report.err.log` |
| スクリプト | `outputs/operator/daily_usage/YYYY-MM-DD/run_0700.log` |

---

## 6. Safety

- credentials / token / `.env`: **コミットなし**
- 送信: `CONFIRM_GMAIL_SEND=YES` + スクリプト内ゲートのみ
- 重複: `email/email_sent.json` 存在時はスキップ（`FORCE_DAILY_GMAIL_SEND=YES` で上書き可）
- 観測のみ · 売買推奨なし · market live HTTP なし

---

## 7. Next

1. **R6.19-E** を `main` にマージ（07:00 日本語本文の恒久化）
2. 翌朝 07:00 後に launchd ログ + 受信確認
3. Mac スリープ時は厳密 07:00 非保証 — 起床後ログ確認
