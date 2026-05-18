# R6.15-A — Daily header · stale outputs · review record

**ステータス**: **ブランチ作業のみ**（**`main` 未反映**）。ブランチ: **`work/r6-15-a-daily-header-stale-output-review-record`**。**`git worktree`**: `/Users/uotani/Projects/invest-alpha-os-r6-15-a`。外部レビュー **F-1 / F-2 / F-3**（品質 HIGH）への対応。

---

## 1. 目的

- **F-1**：`alpha-os daily` 冒頭の **Phase 0 / Phase 1a stub** 表現を実態（momentum cache レポート）に合わせる。**表示文言のみ**。
- **F-2**：指定の **future stale output**（`2031-07-15`）がローカルにあれば **削除**（**単一ファイル `rm`**。**`rm -rf` 不使用**）。
- **F-3**：**`docs/review_integrated_20260515.md`** を **品質レビュー記録**として **Git 管理**（secret grep 済み）。
- **`main` マージ・live HTTP・production cache write・Veto / US 既定変更・worktree cleanup は行わない**。

## 2. 非目的

- **Pull Request**（本フェーズ）。**`r6-10-g` 操作**。**`git worktree remove`**。**branch / remote branch 削除**。**`alpha-os pack` の全面改稿**。

## 3. F-1（daily header）

**対象**: `src/invis_alpha_os/cli/main.py` — **`daily()`** の `report_body` 先頭。

**旧**: `Phase 0 dummy report.` / `- Observation only` / `- No auto trading` / `## Japan Signals` / `- Phase 1a stub` / …

**新**: `Observation only — no auto trading.` / `## Japan Signals — Momentum Cache` / `- Watchlist count` → `- {jq_line}`。

**テスト**: **`tests/test_us_signals_report_opt_in.py`** の golden を最小更新。

## 4. F-2（stale outputs）

| パス | Git | 実施 |
|---|---|---|
| `outputs/reports/daily/2031-07-15.md` | **untracked**（`.gitignore`） | 存在時 **`rm`**（commit 対象外） |
| `outputs/research_packs/7011_2031-07-15.md` | **untracked** | 同上 |

**他の `outputs/**` は触らない**。

## 5. F-3（review record）

- **ファイル**: `docs/review_integrated_20260515.md`（**315 行**・先頭は統合レビューレポート見出し）。
- **secret grep**（`AKIA` / `SECRET=` / `TOKEN=` / `JQUANTS_API_KEY=` / private key / `sk-`）：**ヒットなし**。
- **本ブランチで `git add` し Git 管理**（**Downloads 側コピーは未操作**）。

## 6. アーキテクチャ確認

- **momentum / Veto 計算ロジック**：未変更。
- **US opt-in default**：未変更。
- **live HTTP / cache write**：追加なし。

## 7. 次候補

- **R6.15-B**: safety gate automation implementation（別承認）。
- **R6.15-C**: US cache population runbook（別承認）。
- **R6.14-J**: cleanup continuation（別承認）。
