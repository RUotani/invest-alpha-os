# Long-Run First 開発ルール導入

日付: 2026-05-29  
ステータス: approved  
関連ファイル: `RULES.md` §4–§5、`AGENTS.md` §2.5、`CLAUDE.md` §2.5、`.cursor/rules/main.mdc`、`.agent/cursor_agent_quality_efficiency_longrun_standard.md`

## 結論(1〜3行)

- Agentの細切れPR・過剰停止を抑え、**承認済み安全範囲内の統合ロングラン**を標準とする。
- PR粒度は「小ささ」より **投資判断AIのボトルネック解消単位** を優先する。
- 同一repoの並行実装PRは禁止のまま。単一Agentのロングラン内連続処理は推奨。

## 確度

- 90%

## 背景

v23–v30 の手動データ・J-Quants 系ロングランで、以下の解釈が Agent に起きやすかった。

```text
1作業 = 1小PR
1確認 = 1Final Report
1ゲート = 1新指示
```

過去の「小さなPRを直列」趣旨の引き継ぎと、禁止ゲートの細分化が、ユーザー期待の「一度の指示でできる限り進める」と逆方向に働いた。

## 採用した変更

### RULES.md §4

- 1 PR = 1 Product theme / ボトルネック解消単位
- 同一ロングラン内の連続処理（CI・merge・再生成・reports sync・approval package）を明示許可
- 並行実装禁止 ≠ 細切れ停止、を明記

### RULES.md §5

- 投資判断AI精度改善ボトルネックを最優先に追加

### AGENTS.md / CLAUDE.md / `.cursor/rules/main.mdc`

- Long-Run First 節を追加
- Final Report ワンクリックMarkdownを再確認

### `.agent/cursor_agent_quality_efficiency_longrun_standard.md`

- §0 定型文を Long-Run First 冒頭文に更新
- §5A Long-Run First Development Rule を新設
- §7 PR粒度に新旧方針・良い/悪い粒度を追記

## 維持する制約（変更なし）

- live HTTP / cache write / actual import / secrets / workflow / pyproject / GitHub settings の無承認実行禁止
- 同一repo並行実装PR禁止（読み取り専用調査のみ並行可）
- main直push・force push・trading recommendation 禁止

## 反証

- PR統合しすぎると review不能・CI切り分け困難（800行目安・1 Product theme は維持）
- 承認スコープ誤解（refresh承認 ≠ import承認）— approval package で境界を明示する運用を継続

## 次アクション

- 新規 Cursor 指示は longrun標準 §0 の定型文を冒頭に含める
- v31以降のロングラン指示は本decisionを前提とする
