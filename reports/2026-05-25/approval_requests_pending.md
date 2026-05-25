# 人間承認リクエスト（未回答）— 2026-05-25

## 3行サマリー
- 前回 `reports/2026-05-24/approval_requests_20260524.md` と同内容を **再掲**（未回答のため）。
- **承認 A（P10 AMD）** が `STOOQ_APIKEY` 未設定で BLOCKED。YES まで live HTTP/cache write しない。
- **承認 B/C/D** は任意。Agent は承認不要の read-only Product のみ継続。

---

<<< ここからコピペして返信 >>>

## 承認 A — P10 tier-1 AMD refresh（必須・現状 BLOCKED）

```text
承認 A: P10 AMD refresh
- YES / NO
- STOOQ_APIKEY: 設定済み（値は貼らない）
- 対象: AMD のみ
- 実行担当: 人間ターミナル / Cursor
- approval ref: （任意）
```

## 承認 B — 週次 observation_log 書込（任意）

```text
承認 B: weekly --write-observation-log
- YES / NO
- 実行日: YYYY-MM-DD
```

## 承認 C — portfolio 進捗 %（任意）

```text
承認 C: portfolio domain %
- 確定値: __% または 要確認維持
```

## 承認 D — Gmail 本番（任意）

```text
承認 D: Gmail send
- YES / NO（dry-run のみ / 本番）
```

<<< ここまでコピペして返信 >>>

---

詳細手順: [approval_requests_20260524.md](../2026-05-24/approval_requests_20260524.md)
