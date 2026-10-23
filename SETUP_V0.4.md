# NEXUS NEWS v0.4 — 無料運用・導入手順

## 目的

現在の公開サイト v0.3 に、発行元RSSの短い概要、AI利用回数の1日上限、運営レポートを追加します。本文の自動スクレイピング、事実を創作したAI要約、無許可のデザイン改変は行いません。

## 必ず最初に行うこと

1. `https://github.com/cxxxxzy/nexus-news` を開き、緑の **Code → Download ZIP** で現状のバックアップを保存する。
2. このパッチの ZIP を Windows の「すべて展開」で解凍する。**ZIPそのものはアップロードしない**。
3. リポジトリの **Code → Add file → Upload files** へ。解凍したパッチの**中身**を、フォルダ構造を保ったままアップロードし、**Commit changes**。
4. 特に **`.github/workflows/publish.yml`** はWindowsの隠しフォルダ扱いで漏れやすいので、GitHubでファイルを開き、`reports/ai-budget.json reports/improvement-proposals.md` を `git add` する行があることを確認。なければZIP内の同名ファイルと**全体を差し替える**。
5. `scripts/free_ai_editor.py`、`scripts/update_news.py`、`scripts/audit_news.py`、`config/sources.json`、`app.js`、`styles.css`、`policy.html`、`tests/test_v04.py`、`reports/ai-budget.json`、`SETUP_V0.4.md` が所定の場所にあることを確認。

**注意：** GitHubのWebアップロードで同名ファイルが置き換えられたか、コミット後に必ず確認してください。`data/news.json` はパッチに含めていません。既存の記事を上書きしません。`dist/` も含めていません（Actionsが再生成します）。

## 動作確認

1. **Actions → Update news and publish** に進む。
2. `push` 自動実行が `build` / `deploy` ともに緑なら、コードと静的サイトの公開処理は成功。**pushではRSS取得とAI生成をスキップする設定です。**
3. **Run workflow → main → Run workflow** で**新しい手動実行**を開始。
4. `build` 内で **Fetch news on schedule or manual run**、**Optional free AI reading guides**、**Audit news quality (no API cost)**、**Unit tests** を確認。
5. AIログは `AI GUIDES: ... new; daily requests used 2/2 JST` 等が目安です。**同じ日本時間の日に2回使い切っていたら生成は0件で正常です。**
6. GitHubの `reports/latest-audit.md` と `reports/improvement-proposals.md` を開き、数値・改善候補を確認。
7. サイトを `Ctrl+F5` で再表示。記事によっては **「発信元が提供する短い概要」** が表示されます。JPCERT/CC のRSSに30文字以上の説明文がある記事のみ対象です。毎日必ず表示されるとは限りません。

## 無料運用

- **既存のCloudflare Secrets/Variablesは変更不要。** `FREE_AI_ENABLED=1` とCloudflareの認証情報を継続利用します。
- 新規の**手動設定は不要**です。`reports/ai-budget.json` が**日本時間の日付で1日2回まで**のAIリクエスト試行を記録します。成功・失敗に関係なく使用数に含みます。
- これはCloudflare のNeurons使用量の上限設定ではありません。**Workers Freeプランを維持**し、Cloudflareダッシュボードで別途利用量を確認してください。無料枠を使い切った場合、AI処理は失敗してもニュース更新は継続します。
- GitHub Actionsの `schedule` は厳密な時刻を保証しません。公開リポジトリで60日間活動がない場合、定期実行が無効になることがあります。
- 元記事の本文・画像を無断収集しません。公式発信者の短いRSS概要にも利用規約・引用要件が適用されます。利用に問題が見つかった場合は `config/sources.json` の `JPCERT/CC 公式RSS` を削除してください。

## 自動化できること／できないこと

- **できる：** 毎日のRSS収集、最大2件のAI読解ガイド生成、品質点検、改善案レポート、静的サイト再生成。
- **まだできない：** 元記事全文を読んで事実確認済みのAI解説記事を無人公開すること、サイトのソースコードをAIが自律的に改修・公開すること。改善案は確認後に別途実装します。

## 問題が起きた場合

- `build` が赤い場合、失敗したステップを展開してログを確認。
- `AI daily budget reached/unavailable` は1日の試行上限到達または台帳エラー。**台帳の数値を手動で戻して再実行しないでください。**
- `HTTP status 401` はトークン、`403` はアクセス権、`429` は割当や回数制限の可能性。
- `.github/workflows/publish.yml` が反映されない場合はファイル全体をGitHub画面で編集し直してください。
- 配信元RSSが停止した場合、従来の記事は残ります。`Audit news quality` で更新日時と最新記事の日時を確認してください。

公式情報:
- https://developers.cloudflare.com/workers-ai/platform/pricing/
- https://docs.github.com/en/actions/reference/events-that-trigger-workflows#schedule
- https://www.jpcert.or.jp/rss/index.html
