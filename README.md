# Exhibit Board

個展・グループ展の開催情報を誰でも登録・誰でも閲覧できるモダンで軽量なイベント掲示板。

## 🎯 概要

SNSで流れがちな展示告知を整理し、会期と場所を迷わず把握できるプラットフォームです。
- **軽量設計**: 画像なし・テキスト中心で高速表示
- **信頼性**: SNS告知URL必須で情報の確からしさを担保
- **使いやすさ**: スマホで見やすいミニマルUI
- **荒らし対策**: reCAPTCHA、レート制限、重複URL禁止

## 🚀 機能

### 実装済み (MVP)
- ✅ イベント登録（タイトル/会期/会場/都道府県/料金/告知URL必須）
- ✅ 公開リスト表示（開始日順/終了済みは非表示）
- ✅ 期間フィルタ（これから/今月/30日以内）
- ✅ 都道府県フィルタ
- ✅ 主催情報リンク（X/Instagram/Threads）
- ✅ 告知URLの表示と遷移
- ✅ reCAPTCHA v3によるボット対策
- ✅ 告知URLドメインチェックと重複禁止
- ✅ レート制限（1IP/1hで最大5投稿）

### 今後の予定
- ⏳ カレンダービュー（月表示）
- ⏳ .ics出力（単体/検索結果）
- ⏳ 簡易承認フロー（pending レビュー）

## 🛠 技術スタック

- **Frontend**: Next.js 14 (App Router)
- **Styling**: TailwindCSS + shadcn/ui
- **Backend**: Vercel Serverless Functions
- **Database**: Supabase (PostgreSQL + RLS)
- **Security**: reCAPTCHA v3, Rate Limiting
- **Deployment**: Vercel

## 🏗 セットアップ

### 前提条件
- Node.js 18+
- npm/yarn/pnpm

### 1. プロジェクトのクローンと依存関係インストール

```bash
git clone <repository-url>
cd exhibit-board
npm install
```

### 2. 環境変数の設定

`.env.local` ファイルを作成：

```env
# Supabase Configuration
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url_here
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key_here
SUPABASE_SERVICE_KEY=your_supabase_service_key_here

# reCAPTCHA Configuration  
NEXT_PUBLIC_RECAPTCHA_SITE_KEY=your_recaptcha_site_key_here
RECAPTCHA_SECRET=your_recaptcha_secret_here

# Rate Limiting Configuration
RATE_LIMIT_MAX=5
RATE_LIMIT_WINDOW=3600
```

### 3. データベースセットアップ

1. [Supabase](https://supabase.com) でプロジェクトを作成
2. `database/schema.sql` を実行してテーブルを作成
3. RLS（Row Level Security）ポリシーを適用

### 4. reCAPTCHA設定

1. [Google reCAPTCHA](https://www.google.com/recaptcha/admin) でv3キーを取得
2. サイトキーとシークレットキーを環境変数に設定

### 5. 開発サーバー起動

```bash
npm run dev
```

http://localhost:3000 でアクセス可能

## 📚 API仕様

### GET /api/events
展示イベント一覧を取得

**Query Parameters:**
- `range`: `upcoming` | `thisMonth` | `next30` (optional)
- `prefecture`: 都道府県名 (optional)

**Response:** `200 Event[]`

### POST /api/events
新しいイベントを登録

**Body:**
```json
{
  "title": "展示タイトル",
  "host_name": "主催者名（任意）",
  "x_url": "https://x.com/...",
  "ig_url": "https://instagram.com/...",
  "threads_url": "https://threads.net/...",
  "venue": "会場名",
  "address": "住所（任意）",
  "prefecture": "都道府県",
  "price": "料金（任意）",
  "start_date": "2025-01-01",
  "end_date": "2025-01-31",
  "announce_url": "告知URL",
  "notes": "備考（任意）",
  "captcha_token": "reCAPTCHA token"
}
```

**Response:**
- `201`: `{ id: string, message: string }`
- `400/422/429`: `{ error_code: string, message: string }`

## 🚢 デプロイ

### Vercelデプロイ

1. [Vercel](https://vercel.com) でプロジェクトをインポート
2. 環境変数を設定
3. 自動デプロイを確認

### 環境変数（本番環境）
すべての `.env.local` の変数を Vercel ダッシュボードで設定

## 🔒 セキュリティ

- **Row Level Security (RLS)**: 読み取りは匿名可、書き込みはAPIロールのみ
- **reCAPTCHA v3**: スコア閾値でpending振り分け
- **レート制限**: 1IP/1hで最大5投稿
- **入力バリデーション**: URL/日付/都道府県/文字数制限
- **ドメイン制限**: 許可されたSNSドメインのみ

## 📝 ライセンス

MIT License

## 🤝 コントリビューション

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📞 サポート

問題や提案がある場合は、GitHubのIssuesをご利用ください。
