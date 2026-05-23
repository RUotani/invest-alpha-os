# peer_sync cache-only MVP

日付: 2026-05-24  
ステータス: approved  
関連ファイル: `RULES.md` §5, `docs/148_product_peer_sync_inventory_and_mvp.md`, `signals/peer_sync.py`

## 結論(1〜3行)

- `signals/peer_sync.py` を cache-only MVP として main Product ラインに追加する。
- 初版は `config/peer_map.yaml` + US daily bars cache のみ。weekly 統合と JP peers は後続 PR。
- 観測ラベルのみ。取引推奨・自動配分は行わない。

## 確度

- 85%

## 背景

- `STATE.md` §7 と `docs/136` で peer_sync が未実装とされ、`RULES.md` も operator 拡張ゲートに peer_sync を要求。
- cross_market discovery は存在するが、anchor→peer 相対リターン監視とは別ドメイン。

## 検討した選択肢

1. 棚卸しドキュメントのみ — ゲート解除に不十分
2. cache-only peer_sync MVP + `validate peer-sync` CLI — **採用**
3. operator-runner へ即統合 — Ops 凍結に反する

## 採用した選択肢の根拠

- momentum / forward validation と同じ cache-only パターンで低リスク
- CLI で週次運用前に smoke 可能
- RULES の「peer_sync シグナル検出」最小要件を満たす

## 反証(bear case)

- peer_map が小さすぎて運用価値が薄い → peer_map / watchlist 拡張で再評価
- JP peers が US cache ローダーでは動かない → JP 専用ローダーが必要と判明したら decision を supersede

## 影響範囲

- 新規: `signals/peer_sync.py`, `product/peer_sync_cache_only.py`, tests, docs/148
- CLI: `validate peer-sync`
- weekly-us-observation: 変更なし（本 decision では触らない）

## 次のアクション

- [x] cache-only MVP + tests
- [ ] weekly cycle opt-in section（別 PR）
- [ ] observation_log peer_sync note 形式（別 PR）
