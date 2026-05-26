# observation_log 重複 ISO 週の整理方針

日付: 2026-05-26  
ステータス: approved  
関連: docs/154, docs/161, `us_forward_p3_stall_diagnosis.py`, PR #280–#283

## 結論

- **P3 forward（normal mode）** では **symbol × ISO 週あたり1行** を有効サンプルとみなす。
- 同一週の2行目以降は `duplicate_same_week_rows` として分類し、**matched 増加に寄与しない**。
- **既存ログの一括削除は行わない**（観測履歴の監査証跡を保持）。新規追記は preflight で重複週を警告し、**新しい ISO 週の初回行のみ**を L1 で積む。

## 確度

- 90%

## 背景

- observation_log **514** 行・US signal 行の大半が同一 ISO 週の重複（~399 行）。
- dedupe counterfactual でも normal matched は **1/10** のまま。
- L1 追加だけでは P3 usable に到達しないことが counterfactual で確認済み。

## 採用した方針

| 操作 | 許可 | 備考 |
| --- | --- | --- |
| read-only 分類・preflight | 常時 | `validate forward-p3-status`, weekly dry-run |
| 新規行の追記（新 ISO 週） | L1 承認時 | `will_be_matchable_after_date_rows` 増加見込み時のみ |
| 同一週の再ログ | 非推奨 | preflight `would_duplicate_count` で警告 |
| ログ行の物理削除 | **禁止**（デフォルト） | 監査・再現性。必要なら別 decision + 明示バックアップ |
| アーカイブ JSONL への移行 | 将来検討 | `observation_log_archive.jsonl` 等・手動 |

## 反証

- 重複行を残す限り、matched は週あたり最大1に近いまま。
- 削除を許すと forward 再計算で matched が跳ねる可能性があるが、**観測履歴の改ざんリスク**が大きい。

## 次のアクション

- [ ] 新 ISO 週が来た週のみ L1（`will_be_matchable_after_date_rows > 0` 時）
- [ ] `validate forward-p3-status` の `p3_us_forward_summary` を週次監視
