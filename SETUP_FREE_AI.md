# NEXUS NEWS v0.2 — 無料AIを有効化する手順（Windows + GitHub）

この版は、現在動いているRSS収集・GitHub Pages公開を残したまま、**Cloudflare Workers AIの無料枠**を使って記事の「確認ポイント（疑問文）」を追加します。**AIは記事本文を読んでおらず、事実確認済みの解説記事ではありません。** 対象は1回あたり最大2件（コード上限は3件）です。

## 先に大切なこと

- Cloudflareの **Workers Free** プランで運用してください。**Workers Paidには変更しないでください。** 無料枠は現時点で10,000 Neurons/日。超過時、Freeプランでは処理が失敗して止まります。無料枠・モデル提供内容は将来変わる可能性があります。
- 使用モデルは `@cf/meta/llama-3.1-8b-instruct-fp8` に固定してあります。高額な有料専用モデルを誤って選択しないため、環境変数からモデルを変更できません。
- AIはオプション。**設定しない場合は今までどおりRSSニュースの自動更新と公開が動きます。** AIの失敗によってRSS更新が停止しない仕組みです。
- GoogleニュースなどRSS提供元の利用条件は別途確認してください。見出しと情報源・リンクのみを収集し、無断で元記事の本文を転載しません。
- ChatGPTのPlus等の契約とAPI利用は無関係です。本版はOpenAIの有料APIには接続しません。

## 手順A：GitHubのコードを更新する

1. このZIPを解凍してください。
2. GitHubリポジトリ `nexus-news` → **Code → Add file → Upload files** で、ZIP内のファイルをフォルダ構造のままアップロードし、既存ファイルは新しい版で上書きします。**ZIP自体はアップロードしません。**
3. **特に `.github/workflows/publish.yml` は前回アップロード時に消えた経緯があるため、必ず個別に確認してください。** 必要ならGitHubの **Code → .github → workflows → publish.yml → 編集（鉛筆マーク）** を開き、ZIP内の同名ファイルの内容を全部貼り付けてCommitしてください。
4. 新規作成した `scripts/free_ai_editor.py` と `tests/test_free_ai_editor.py` がそれぞれ正しいフォルダに存在するか確認してください。
5. `Code` 画面に現在の記事データ `data/news.json` が残っていることを確認してください。ZIPにはアップロード時点の記事データを含みます。更新日時が古い場合は、後述の `Run workflow` で新しいニュースに更新してください。

## 手順B：Cloudflare無料アカウントを準備する

1. https://dash.cloudflare.com/sign-up でアカウントを作成、またはログインしてください。
2. **Workers & Pages → Workers AI** を探し、**Use REST API** を選びます。UIの文字が変わった場合は公式 https://developers.cloudflare.com/workers-ai/get-started/rest-api/ を参照してください。
3. **Create a Workers AI API Token** で専用のAPIトークンを発行してください。
4. **Account ID** と **API Token** の2つを手元に保管してください。**このチャットには貼り付けず、GitHubのSecretsにのみ登録**してください。
5. Cloudflareのプラン表示が **Workers Free** であることを確認してください。

## 手順C：GitHub Secretsに登録する

GitHub `nexus-news` → **Settings → Secrets and variables → Actions**

「Secrets」タブ → **New repository secret** を2回使って登録します。

| Name | Secret（値） |
|---|---|
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflareの Account ID（32桁の英数字） |
| `CLOUDFLARE_API_TOKEN` | Cloudflareで発行した Workers AI 専用API Token |

**Variables** タブ → **New repository variable** で以下を追加：

| Name | Value |
|---|---|
| `FREE_AI_ENABLED` | `1` |

この変数が `1` でなければAIは実行されません。**無料枠が心配なら、`0`にするだけでAI処理をオフにできます。** RSS自動更新は継続します。

**追加不要：** `OPENAI_API_KEY`、`AI_EDITOR_ENABLED`、`OPENAI_MODEL`。昔の版で登録したものがあれば、今回のプログラムからは使用されません。

## 手順D：動作確認

1. GitHub → **Actions → Update news and publish** → **Run workflow** → `main` を選んで実行。
2. `build` のログで **Fetch news on schedule or manual run** に続き、**Optional free AI reading guides** を開きます。
3. `AI GUIDES: 2/2 new (max 3 requests/run)` のようなログが出れば、今回のAI追加処理が成功しています。候補不足の場合などは件数が少なくなることもあります。
4. `deploy` が緑色で成功したら、 https://cxxxxzy.github.io/nexus-news/ を再読込。AIが生成した記事に **AIの確認ポイント** と表示され、記事をクリックすると質問文を確認できます。

## よくある現象

- `AI disabled: missing Cloudflare Account ID or API token` → Secretsを確認。
- `AI disabled: FREE_AI_ENABLED is not 1` → Variablesを確認。
- `Workers AI HTTP status 401/403` → APIトークンの権限・モデル提供状況・プランを確認。秘密情報をログやチャットに貼らない。
- `AI free quota/rate limit reached` → 本日のAI処理を停止。翌日に再実行するか、翌日の定期更新を待ちます。無料枠を超えるために有料プランにする必要はありません。
- `AI GUIDES: 0/0 new` → 最近48時間以内のAI未処理記事が無い場合。最新RSS収集が成功しているかを確認。
- `AI GUIDES: 0/2 new` → モデルが形式に合う疑問文を返さなかった、またはAPIに接続できなかった場合。RSS公開は継続します。
- `Node.js 20 is deprecated` 警告 → GitHubが使用するActionの互換性警告で、AI生成のAPI認証エラーとは無関係。緑色で成功なら直ちに失敗したわけではありません。

## 毎日の運用

`publish.yml` の定期実行は日本時間6:17頃（GitHub側の遅延あり）。AI生成は成功した記事にだけ保存され、次回ニュース収集で同じ記事を再取得しても同じ質問を保持します。ただし手動で何度も実行すると追加でAPIを使用する可能性があり、無料枠を消費します。

**無料枠利用量はCloudflareのWorkers AIダッシュボードで確認**してください。Freeプランの利用量を超えるとAI側が失敗しますが、そのためにサイトの更新を停止しない設計です。

## 制約と今後の拡張

見出しだけを渡しているため、AIが事実確認済みの独自ニュース記事を作れるわけではありません。記事本文の権利を確認できる情報源を用意し、検証と編集承認を整備するまでは、AI生成の断定的な解説を自動公開しない方針です。

参考（公式）：
- https://developers.cloudflare.com/workers-ai/platform/pricing/
- https://developers.cloudflare.com/workers-ai/get-started/rest-api/
- https://developers.cloudflare.com/workers-ai/models/llama-3.1-8b-instruct-fp8/
