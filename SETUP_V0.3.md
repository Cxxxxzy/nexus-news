# NEXUS NEWS v0.3 導入ガイド（無料構成・Windows）

このパッチは **既存リポジトリの `data/news.json` を含みません**。現在の記事、AI生成済みデータ、GitHub Secretsを維持します。

## 事前確認

- GitHubリポジトリ：`nexus-news`（`main` ブランチ）
- 現在の実行 #13 でニュース収集・無料AI生成・サイト公開の成功を確認済み
- Cloudflare Workers Freeプランを継続（有料プランに変更しない）
- GitHub Secrets：`CLOUDFLARE_ACCOUNT_ID` / `CLOUDFLARE_API_TOKEN` はそのまま
- GitHub Variable：`FREE_AI_ENABLED = 1` はそのまま

## 手順1：バックアップ

1. `https://github.com/cxxxxzy/nexus-news` を開く。
2. **Code → Download ZIP** で現行ファイルをバックアップする。
3. `main` の現在のActions実行結果が成功していることを確認する。

## 手順2：v0.3のファイルを反映

1. `NEXUS_NEWS_v0.3_PATCH.zip` をWindowsで解凍する。
2. GitHub → **Code → Add file → Upload files** を開く。
3. 解凍した `UPLOAD_THIS` 内の **ファイルおよびフォルダ**をGitHubにアップロードする。ZIPファイルそのものや `UPLOAD_THIS` フォルダ自体はアップロードしない。
4. **Commit changes** を押す。既存ファイルと同名のものは、新しい内容に更新する。
5. GitHubの `Code` 画面に以下が存在することを確認する。
    - `scripts/audit_news.py`（新規）
    - `scripts/free_ai_editor.py`（更新）
    - `scripts/build_site.py`（更新）
    - `tests/test_v03.py`（新規）
    - `.github/workflows/publish.yml`（更新）
6. **重要：** `.github/workflows/publish.yml` がアップロードされなかった場合は、Code画面から既存の同名ファイルを開き、鉛筆マークからZIP内の同名ファイルの内容に丸ごと置き換え、Commitしてください。旧版のままだと監査ステップが表示されません。

## 手順3：初回公開の確認（APIを再発行する必要はありません）

ファイルをCommitすると`push`による自動テスト・公開が走ります。`push`ではニュース取得とAI生成がスキップされることは **正常** です。以下を確認してください。

- Actions → `Update news and publish` → 最新の実行で build / deploy が緑色
- `Audit news quality (no API cost)` が実行される
- 新規テストが合格する
- 公開サイトに「ニュース更新状況」が表示される

## 手順4：無料AIの3つの読解ポイントをテスト

1. Actions → **Update news and publish** → **Run workflow**（**Re-run jobs**ではない）で`main`を実行する。
2. buildログの`Optional free AI reading guides`を開く。
3. `AI GUIDES: 2/2 new ...`などのログが出たら成功した記事がある。候補不足では件数が0になることもある。
4. Deployの成功後、公開サイトを `Ctrl + F5` で再読込する。
5. **新しくAIを生成した**記事を開くと、最大3つの質問が表示される。v0.2で既に生成された記事は古い1問を保持する。過去記事を無断で書き換えない安全仕様。

## 手順5：毎日の監査レポート

- スケジュール実行は日本時間 06:17頃（遅延や失敗の可能性あり）。
- `reports/latest-audit.md` が日次実行時に更新され、記事数、カテゴリ、更新の遅れ、AIガイド件数を記録する。
- GitHub Actions内で `Audit news quality (no API cost)` のログを確認できる。
- 公開サイトの `data/health.json` には公開時点の監査スナップショットを出力する。
- サイトの表示時点で最終更新が36時間を超えると注意表示を出す。

## 完全無料運用の注意

- OpenAI APIは使わない。
- Cloudflare Workers Freeの無料割当を使う。既存プログラムの上限は1回最大3リクエストで、現在のActions設定では**1回2記事**。各記事で最大3質問を1回のAI API呼び出しで作る。
- 無料枠は変更される可能性がある。FreeプランからWorkers Paidに変更しない。
- 外部ニュース本文を自動転載しない。現状は **見出しの読解支援** であり、検証済みの独自ニュース記事ではない。
- 記事の出典のRSS自体も、配信元の利用規約に従うこと。
- GitHub Actionsの定期実行は遅延・停止する可能性があり、永続的な無人運営の保証ではない。
- 今回の「改善」機能は自動監査まで。本番HTML/CSS/JSをAIが勝手に書き換えない。変更はテストと人間の承認を経て行う。

## よくあるエラー

| 表示 | 対応 |
|---|---|
| `AI GUIDES: 0/2 new` | AIレスポンスが不適切、対象記事不足、または接続問題。ログを確認 |
| `Workers AI HTTP status 401` | 既存のGitHub Secretsの値とWorkers AI権限を確認。キーを公開しない |
| `HTTP status 429` | 無料枠/レート制限。無理に再実行せず翌日の更新を待つ |
| `IndentationError` | `scripts/free_ai_editor.py`を部分編集せずパッチ版で丸ごと置換 |
| ActionsのAIステップがスキップ | `push`実行なら正常。`Run workflow`で手動実行 |
| `deploy`失敗 | Actionsのbuild/deployログを確認し、直近変更の差分を点検 |

## 開発者向けオフラインテスト

```bash
python -m unittest discover -s tests -v
python scripts/audit_news.py
python scripts/build_site.py
```

`dist/` は生成物で、GitHubへ手動アップロードする必要はありません。
