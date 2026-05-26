# 承認回数最小化 — 運用見直し（2026-05-26）

## 結論

**wave ごとの `承認 AQ: YES` / `承認 AR: YES` は廃止**し、**3 種類のバッチ承認**に集約する。  
あわせて **matched=3 のまま weekly+P10 を毎回回すのは停止**し、Agent は **product（US forward 10/10）と read-only 診断**に集中する。

詳細は運用中 · `approval_requests_pending.md` 参照。
