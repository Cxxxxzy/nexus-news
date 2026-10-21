# NEXUS NEWS — 総合ニュースサイト無料AI編集補助版 v0.2

日本語の総合ニュースポータル。ニュース見出し・公開日時・出典・元記事リンクをRSSから収集し、静的なWebサイトを毎日更新します。

> **ステータス**: ニュース取得・GitHub Pagesへの公開機能は実運用済み。v0.2ではCloudflare Workers AI（無料枠）の任意機能を追加しました。APIトークン未設定では今までどおりRSSだけ更新します。ニュース本文を検証済みの独自解説はまだ実装していません。

**無料AIを有効化する最初の手順は [`SETUP_FREE_AI.md`](SETUP_FREE_AI.md) をご覧ください。**

## 主な機能

- PC / スマートフォン対応の日本語サイト
- 8カテゴリ（国内、国際、政治、経済、テクノロジー、科学、スポーツ、エンタメ）
- キーワード検索（Ctrl+K）、カテゴリ切替、新着・古い順、もっと見る
- ブックマーク、ダークモード（各ブラウザ内のlocalStorage）
- RSS取得、URLとタイトルによる重複排除、最大120件保存
- 毎日06:17 JST目安の自動更新 / GitHub Pages公開用Actions
- 投稿データと公開ファイルだけをビルド出力。APIキー等は公開しない
- AIオプション：Cloudflare Workers AI無料枠による**見出しベースの読者向け確認質問**生成（記事本文の要約ではない）

## 1. すぐにローカル表示（Windows）

**いちばん簡単:** ZIPを展開して `PREVIEW.html` をダブルクリックしてください。サンプル記事のデザイン・検索・ブックマークをネット接続なしで試せます（デモ専用で、毎日更新されるサイトではありません）。

本番に近い構成で見る場合：

1. ZIPを展開する
2. Python 3があれば、`START_WINDOWS.bat`をダブルクリック
3. ブラウザで `http://localhost:8000` にアクセス

コマンドプロンプトなら：

```bat
cd /d C:\path\to\nexus-news-starter
py -3 -m http.server 8000
```

`index.html` をファイルとしてダブルクリックすると、ブラウザの制限により`data/news.json`を読めない場合があります。必ずローカルHTTPサーバー経由で開いてください。

## 2. オフラインでテスト

```bat
py -3 -m unittest discover -s tests -v
py -3 scripts\update_news.py --fixture tests\fixtures\sample_feed.xml --dry-run
py -3 scripts\build_site.py
```

`--fixture ... --dry-run` は本番データを変更しません。テスト用RSSに収録されている架空の見出しで動作を確認できます。

## 3. 実際のニュースを収集

RSSが利用できるネットワークで：

```bat
py -3 scripts\update_news.py
```

`data/news.json`が実データに置き換わり、デモ表示が消えます。情報源は `config/sources.json` で変更できます。**外部RSSが取得できなかった場合はエラー終了し、既存データを破壊しません。**

RSSリンクはニュース提供者の規約や仕様変更により利用できなくなることがあります。初期版に記載したGoogle ニュースのカテゴリ別RSSは、本番での接続検証をまだ完了していません。公開前に取得可否・利用条件を確認してください。

## 4. GitHub Pagesで無料公開する

1. [GitHub](https://github.com/)でアカウントを作成する
2. 新しい**公開リポジトリ**を作り（例：`nexus-news`）、ZIP展開後のファイルを全部アップロードする（`.github`フォルダも含む）。デモだけなら秘密情報は含まれません
3. ブランチ名を `main` にする
4. リポジトリの **Settings → Pages → Build and deployment → Source** を **GitHub Actions** にする
5. **Actions** タブで `Update news and publish` を開き、`Run workflow` で初回手動実行する
6. Actionsの実行が成功したら `https://ユーザー名.github.io/nexus-news/` で確認（名称はリポジトリに合わせる）

GitHub Actionsの定期ジョブは正確な時刻に開始する保証がありません。60日間リポジトリにアクティビティがない場合、公開リポジトリのスケジュールは自動的に無効になることがあります。スケジュールと運用ログは定期的に監視してください。

**注意：** GitHub Pagesは公開サイトです。公開前に運営者名・問い合わせ先・プライバシー表示・著作権対応方針などを確認してください。

## 5. 無料AI編集サポート（任意）

**OpenAIの有料API接続は削除しました。** 本バージョンはCloudflare Workers FreeプランのREST APIに対応し、無料枠で記事の確認ポイントを生成します。AIは本文を取得しません。機能はデフォルト無効なので、GitHubにコードをアップロードしただけではAPI料金が発生しません。

GitHub Secretsの設定、無料プラン確認、動作テストまでの日本語手順は **[`SETUP_FREE_AI.md`](SETUP_FREE_AI.md)** を参照してください。

**注意:** Workers Freeで提供される1日あたりの無料割当は現時点では10,000 Neuronsです。提供条件変更・容量制限・レート制限があり、無料枠を超えるとAI処理は停止します。Workers Paidにアップグレードしないでください。

## 6. 将来の開発ロードマップ

- v0.2: Cloudflareの無料AIによる読者向け確認質問（今回追加）
- v0.3: 編集者レビュー画面、下書き / 承認 / 公開ワークフロー、訂正機能
- v0.4: 記事本文の権利ある情報へのアクセスを前提とする、出典付きAI解説記事
- v0.5: アクセス解析、SEO、改善提案の定期レポート、プレビューと承認付きUI更新

AIが本番サイトのプログラムを無制限に自己改変する設計は採用しません。変更はブランチ/プルリクエストで提案し、テストと承認を経て公開します。

## ファイル構成

```text
nexus-news-starter/
├── SETUP_FREE_AI.md      無料AIの導入手順
├── PREVIEW.html           1ファイルのオフライン表示デモ
├── index.html             ホームページ
├── styles.css             PC/スマホ対応のデザイン
├── app.js                 カテゴリ・検索・記事保存・表示
├── policy.html            編集方針
├── privacy.html           プライバシー表示
├── assets/favicon.svg     アイコン
├── data/news.json         現在の記事データ（初期はデモ）
├── config/sources.json    RSS情報源
├── scripts/update_news.py RSS取得・重複削除・AIメモ保存
├── scripts/free_ai_editor.py Cloudflareの任意AI確認ポイント
├── scripts/build_site.py  公開用ファイル生成
├── scripts/build_preview.py オフラインプレビュー生成
├── tests/                 単体テストとオフライン用RSS
├── .github/workflows/publish.yml 定期取得・テスト・デプロイ
├── START_WINDOWS.bat      Windows用起動スクリプト
└── README.md              この手順書
```

## 情報源・著作権について

- この初期版は**ニュース本文をコピーしません**。見出し、出典、公開日、元リンクのみを取得します
- 見出しも著作権・利用条件が無制限に自由とは限りません。提供元のRSS・商用利用規約を事前に確認してください
- RSSの配信停止、URL変更、不正なメタデータなどによる障害に備えてログと運用監視が必要です
- 実ニュースへの自動公開は正確性、出典、権利処理、訂正対応を整備してから始めてください

## 完了済み / 未完了

| 項目 | 状態 |
|---|---|
| サイト表示・レイアウト | 実装済み |
| ローカル検索・ブックマーク | 実装済み |
| RSS処理コード | 実装済み・オフラインのfixtureでテスト |
| 外部RSSへの実アクセス | **未検証** |
| GitHub Actionsのデプロイ | ワークフロー作成済み・GitHub上の実行は未検証 |
| OpenAI API | オプション実装済み・実キーでの動作は未検証 |
| 独自AI解説記事の自動生成と公開 | 未実装 |
| Webサイトの自律改修 | 未実装（承認制を予定） |
