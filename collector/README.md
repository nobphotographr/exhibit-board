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
GitHub ActionsでXを毎時取得します。公開リポジトリのためActions利用料はかからず、
必要なSecretsは`X_BEARER_TOKEN`と`COLLECTOR_API_KEY`です。

## Official venue sites

公式サイトは1日1回だけ取得します。現在の対象はフジフイルム スクエア、キヤノンギャラリー、
Sony Imaging Gallery、JCIIフォトサロンです。

```bash
.venv/bin/python collector/website_collect.py --env-file /path/to/.env --dry-run
```

```cron
42 5 * * * cd /opt/exhibit-board && .venv/bin/python collector/website_collect.py --env-file /opt/exhibit-board/.env >> /var/log/exhibit-venues.log 2>&1
```

公式会場の本番取得もGitHub Actionsで毎日05:42（日本時間）に実行します。
