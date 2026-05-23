# R7.0 — Product Pivot: Investment Signals Pack

**作成**: 2026-05-23  
**前提**: R7.0-Ops-I12-A (PR #204) merge後、Ops拡張を凍結し本ドキュメントのタスクへ移行する。

---

## なぜ今ここへ戻るか

直近30日のPR履歴（#133〜#202）を見ると、ほぼ全てがOps自律開発基盤のドキュメント・テスト・スクリプトだった。  
12h runが18分で終了した原因は**wave設計の欠陥ではなく、キューに高価値の投資プロダクトタスクが不足していたこと**。  
Ops基盤をさらに拡張しても、この問題は解決しない。

---

## 現在の投資プロダクト状態（2026-05-23時点）

### 利用可能なデータ
- **US cache**: 16シンボル（AAPL, AMZN, COIN, GLDM, GOOGL, MARA, META, MSFT など）
- **JP cache (J-Quants)**: 約42ファイル（Core50の一部）
- **signals/momentum.py**: 実装済み（468行、21関数）— score_v2, volume_spike, breakout 等
- **risk/veto_rules.py**: 実装済み — VetoEngine, build_momentum_veto_result
- **discovery**: US/JP universe scanner 実装済み（cache-only）
- **reports/daily_email.py**: 実装済み（Gmail gated delivery）

### 未着手・未完成
- `peer_sync.py` — **未実装**（ファイルなし）
- signals → veto → daily report のend-to-end **weekly 運用** — 未確立
- observation_log への signals 書き込み — outputs/signals/ が空
- US cache 拡張（16シンボルから US universe scanner 対象へ）
- JP Core50 cache カバレッジ（現状 ~19/50）

---

## 優先タスク（Ops凍結中に実装するもの）

### P1 — Signals end-to-end 動作確認（最高優先）

**目標**: `operator-runner` or CLIコマンド1本で、US cache → momentum → veto → markdown report が出力される状態にする。

**タスク**:
1. `operator-runner signals-preview` または `cli signals-run --cache-only` コマンドの動作確認
   - 既存の `render_momentum_signals_cache_only_section` が正しく動くか smoke test
   - 出力が `outputs/signals/` に保存されるか確認
2. veto engine が US 16シンボルに対して正しく評価されるか確認
3. daily report に signals セクションが含まれる状態で `--dry-run` 生成

**検証コマンド（既存CLIを確認）**:
```bash
.venv/bin/python -m invis_alpha_os.cli.main signals-cache-only-preview --help 2>/dev/null || \
.venv/bin/python -m invis_alpha_os.cli.main --help | grep -i signal
```

### P2 — US cache 拡張（16 → 30+ シンボル）

**目標**: US universe scanner が見つけた候補銘柄のうち、stooq cache にデータが存在するものをキャッシュへ追加する。  
**方針**: live HTTP なし — `us_provider_cache_preview_batch` を使い、既存データがあるシンボルのみ取り込む。

### P3 — JP Core50 cache 補完（19/50 → 35+）

**目標**: J-Quants gated ingest でバッチサイズ≤3、日付範囲短縮で残り31銘柄の一部を追加。  
**前提**: レート制限/プラン確認済みであること（B3R の教訓）。

### P4 — weekly observation cycle の確立

**目標**: 毎週月曜に以下が手動1コマンドで実行できる状態にする:
1. signals-preview（cache-only）
2. veto評価
3. daily report生成（dry-run）
4. observation_log への記録

---

## PR境界（提案）

| PR | 内容 | リスク |
|---|---|---|
| #204（現在open） | autopilot-status hotfix | Low |
| #205 | Signals end-to-end smoke + daily `--us-momentum-section` | **merged** `6185b95` |
| #206 | MSFT/AAPL cache refresh runbook | **merged** `deb1599` |
| #207+ | observation_log batch + AAPL fixture + cache refresh execution | Low–Medium |
| #207 | JP Core50 cache 補完 batch 2 | Medium（J-Quants gated） |
| #208 | weekly observation CLI コマンド整備 | Low |

---

## 凍結解除トリガー（再掲）

以下のどれか1つを達成したら、Ops拡張（safety-classify / wave runner）の再開を検討する:
1. US signals の cache-only weekly 運用が2週間継続
2. US/JP end-to-end パイプラインで veto → daily report が安定動作
3. observation_log に30件以上のシグナル記録が蓄積

---

## 参照

- Ops凍結宣言: [docs/01_development_status.md — Ops Freeze セクション](./01_development_status.md)
- autopilot-status: [docs/135](./135_r7_0_ops_i12_a_autopilot_status.md)
- post-run integrator: [docs/133](./133_r7_0_ops_j_post_run_integrator_plan.md)
- effective 12h design (凍結): [docs/134](./134_r7_0_ops_i12_effective_12h_design.md)
