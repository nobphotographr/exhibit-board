# Exhibit Board collector

XのRecent Searchから国内の写真展告知を低頻度で取得し、公開前の候補キューへ送ります。
X本文や添付画像は保存せず、抽出した開催情報、投稿ID、投稿URL、本文ハッシュだけを保存します。

## Environment

```env
X_BEARER_TOKEN=...
COLLECTOR_ENDPOINT=https://exhibit.iruagaru.com
COLLECTOR_API_KEY=...
```

`COLLECTOR_API_KEY`はVercelと収集VPSのみに設定します。

## Dry run

```bash
python -m venv .venv
.venv/bin/pip install -r collector/requirements.txt
.venv/bin/python collector/x_recent_search.py --env-file /path/to/.env --dry-run
```

初回取得は既定で直近6時間だけです。通常運用では`.collector-state.json`の`newest_id`以降のみを取得します。

## Suggested cron

```cron
17 * * * * cd /opt/exhibit-board && .venv/bin/python collector/x_recent_search.py --env-file /opt/exhibit-board/.env --state-file /var/lib/exhibit-collector/x-state.json >> /var/log/exhibit-collector.log 2>&1
```

本番稼働前にVPSをUbuntu LTSへ移行してください。

現在の本番運用ではVPSを使わず、`.github/workflows/collect-exhibitions.yml`の
GitHub ActionsでXを毎日06:17（日本時間）に取得します。公開リポジトリのためActions利用料はかからず、
必要なSecretsは`X_BEARER_TOKEN`と`COLLECTOR_API_KEY`です。

## Official venue sites

公式サイトは1日1回だけ取得します。メーカー系会場、美術館、独立系ギャラリーなどの専用収集に加え、
Photo & Culture, Tokyoの開催一覧を会場発見用のインデックスとして利用します。後者は各記事から
会場詳細と公式告知URLを辿り、公式URLを確認できた展示だけを公開対象にします。SNS共有リンクや
公式サイトが確認できない記事は取り込みません。

日本写真家協会、全日本写真連盟、CAPA CAMERA WEB、ナショナル・フォートの写真展一覧も
発見元として巡回します。公式会場URLが掲載されている場合は公式URLを優先し、団体会員から
提供された展覧会情報は団体ページを出典として明示します。

```bash
.venv/bin/python collector/website_collect.py --env-file /path/to/.env --dry-run
.venv/bin/python collector/photo_culture_collect.py --env-file /path/to/.env --dry-run
.venv/bin/python collector/directory_collect.py --env-file /path/to/.env --dry-run
```

```cron
42 5 * * * cd /opt/exhibit-board && .venv/bin/python collector/website_collect.py --env-file /opt/exhibit-board/.env >> /var/log/exhibit-venues.log 2>&1
```

公式会場の本番取得もGitHub Actionsで毎日05:42（日本時間）に実行します。

Photo & Culture, Tokyoの登録会場全体を再点検するときは次を実行します。これは日次処理には含めません。

```bash
.venv/bin/python collector/photo_culture_audit.py --output collector/photo_culture_venues.json
```

出力には各会場を`official_website`、`social_only`、`no_official_url`、`fetch_error`に分類した結果を保存します。
