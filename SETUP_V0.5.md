# NEXUS NEWS v0.5 — Windows / GitHubでの導入手順

## 0. 前提

- すでに公開されている `nexus-news` リポジトリに **v0.4** が導入されている。
- GitHub Pages が稼働し、GitHub Actions の `build` と `deploy` が成功している。
- Cloudflare Secrets (`CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN`) と Variable (`FREE_AI_ENABLED=1`) は**変更不要**。
- **支払い設定やCloudflare有料プランへの切り替えはしない**。無料割り当てを超えるAI処理は停止する。

## 1. 先にバックアップ

GitHub の `nexus-news` → **Code → Download ZIP** を押し、現在のソースを保存する。

## 2. 修正パッケージを反映

1. `NEXUS_NEWS_v0.5_PATCH.zip` をWindowsで「すべて展開」する。
2. GitHubで `nexus-news` → **Code → Add file → Upload files** を開く。
3. 展開した中のファイルとフォルダを階層を崩さずにアップロードし、**Commit changes** で保存する。
4. 特に `.github` はWindows/ブラウザで見落としやすいため、GitHub上で **`.github/workflows/publish.yml`** を直接開き、次の記述があるか確認する。
   - `timezone: 'Asia/Tokyo'`
   - `Decide whether this run needs a news refresh`
   - `Optional free AI grounded reading guides`
5. 上記が古い場合、GitHubで `.github/workflows/publish.yml` を開き鉛筆マークから**ファイル全体をパッケージ版へ置き換え**てCommitする。
6. GitHub上に **`scripts/should_update.py`** と **`tests/test_v05.py`** が新しく追加されたか確認する。

**注意：** ZIPの中の `data/news.json` や `reports/ai-budget.json` は含まれていません。既存の記事データやAI予算記録を、古いファイルで上書きしないでください。ZIP自体をそのままGitHubにアップロードしないでください。

## 3. 動作確認

1. コードのコミットによる自動実行では、RSS・AI生成は**スキップが正常**です。まず `build` と `deploy` が緑色で終わるか確認。
2. GitHub → **Actions → Update news and publish → Run workflow → main** で新しい手動実行を起動。
3. `build` のログを展開し、次を確認。
   - `Decide whether this run needs a news refresh` → `refresh=true`
   - `Fetch news if due` → RSSが保存される
   - `Optional free AI grounded reading guides` → `GROUNDED AI GUIDES: n/m new; daily requests used ...`
   - `Audit news quality (no API cost)` → `NEWS AUDIT: ...`
   - `Unit tests` → 45件以上 `OK`
4. `deploy` の緑色チェックを確認したら、公開サイトを `Ctrl + F5` で再読込。
5. AIが新形式で生成された記事だけ、**AIの確認ポイント**が表示される。記事を開き、見出しに存在する語句が質問内にそのまま使われているか確認する。
6. 旧形式のAIガイドは表示されません。毎日最大2件ずつ原文照合版に置き換わります（AIの返答形式が不正なら0件もあります）。

## 4. 毎日の自動運用

- 毎朝 **06:17 JST** に自動ニュース更新・AI生成を試みる（GitHub側で遅延や未実行の可能性あり）。
- 毎日 **18:43 JST** に予備確認する。朝の更新が成功して16時間以内ならRSS/AIをスキップ。朝の更新が止まっている場合だけ再実行する。
- GitHubで定期実行が無効化されていないか、時々Actionsの履歴を確認する。公開リポジトリでは、60日間活動がないとスケジュールが停止する場合がある。
- Cloudflare無料枠は **10,000 Neurons/日（UTC 00:00更新）**。サイト側はJSTで最大2リクエストの独自上限を設けているが、AI負荷・他プロジェクトでの利用もあるため、消費Neuronsの上限を完全には保証しない。

## 5. うまくいかないとき

- **Actionsに新ステップがない** → `.github/workflows/publish.yml` を上書きできているか確認。
- **AIが0件** → `reports/ai-budget.json` がその日の2回に達していないか／Cloudflareの無料枠とLogsを確認。旧形式ガイドの表示が一時的に減るのは仕様。
- **API 401/403** → GitHub SecretsやCloudflare権限を確認。API Tokenの実際の値はチャットや公開Issueに貼らない。
- **警告が出る** → 最新のGitHub Actionsログ、`reports/latest-audit.md` を確認。
- **更新スケジュールが動かない** → まず手動Run workflowで検証。毎日指定時刻ぴったりの実行は保証されない。
- **ファイルアップロードの途中でエラー** → 先に戻す場合はGitHub上の該当コミットをRevertし、動いていた版に復旧する。

## 6. 確認していないこと

このZIPはオフラインテストに合格していますが、ユーザーの本番GitHub Actionsと実際のCloudflare AIへの応答は未検証です。GitHubに反映後、手動実行ログで確認してください。
