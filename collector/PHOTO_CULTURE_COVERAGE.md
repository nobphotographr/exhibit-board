# Photo & Culture, Tokyo 会場カバレッジ

最終監査日: 2026-08-13

`gallerylist.php`に登録されている460会場を`photo_culture_audit.py`で棚卸しした。
全件の会場名、地域、住所、会場詳細URL、公式URL、判定理由は
`photo_culture_venues.json`に記録している。

## 監査結果

- 公式Webサイトあり: 435会場
- SNSのみ: 12会場
- 公式URLの登録なし: 13会場
- 詳細ページ取得失敗: 0会場

Photo & Culture, Tokyoの開催一覧は、会場を発見するための日次インデックスとして利用する。
開催記事に紐づく会場詳細から公式サイトを確認できる展示だけを取り込む。記事に個別の公式告知URLが
あればそれを優先し、なければ会場公式サイトを使用する。共有ボタン、SNSのみ、公式URLなしの展示は
この経路から公開しない。

## SNSのみ

- Hi Bridge Books
- AA
- 東條會舘写真研究所
- THE NORTH FACE STANDARD 二子玉川
- RABA[Rich & Busy Asakusa]
- Park!Park!Park!
- 書肆ひるね
- BLUE HOUSE STUDIO
- リバーブックス
- BD Gallery
- かまどの下の灰までgallery
- 本と自由

## 公式URLの登録なし

- 柿の木荘
- 渋谷ヒカリエ8/Cube
- LUMIX BASE TOKYO
- see you gallery
- Gallery E&M nishiazabu
- Space2*3
- 七軒長屋 元居酒屋「かずの子」
- REMINDERS PHOTOGRAPHY STRONGHOLD
- 横浜開港資料館
- Photo Gallery &Photobooks Cafe 芥
- ギャラリー二等車
- ループハウス
- 高知県立美術館

この分類はPhoto & Culture, Tokyo側の登録状況を表す。公式URL未登録でも、開催記事内に主催者・会場の
個別公式告知がある場合は日次収集できる。Gallery F16とHuBaseは独立した開催予定ページを確認できないため、
現時点では日次X収集で告知を補完する。
