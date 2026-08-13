import unittest
from datetime import datetime, timezone

from collector.extract import extract_event


PUBLISHED = datetime(2026, 8, 13, tzinfo=timezone.utc)


class ExtractEventTests(unittest.TestCase):
    def test_extracts_full_japanese_date_range_and_labeled_venue(self):
        text = """山田花子 写真展「光の岸辺」
日時：2026年8月20日（木）～8月30日（日）
展示会場：青山フォトギャラリー
東京都港区青山1-2-3
入場無料"""

        result = extract_event(text, PUBLISHED, "100")
        event = result["extracted"]

        self.assertEqual(event["title"], "光の岸辺")
        self.assertEqual(event["venue"], "青山フォトギャラリー")
        self.assertEqual(event["prefecture"], "東京都")
        self.assertEqual(event["start_date"], "2026-08-20")
        self.assertEqual(event["end_date"], "2026-08-30")
        self.assertEqual(event["price"], "無料")
        self.assertEqual(result["confidence"], 1.0)


    def test_infers_year_and_end_month_when_omitted(self):
        text = """写真展に出展のお知らせ
【Osaka Street Photography】
8月13日(木)～18日(火)
大阪・道頓堀 ギャラリー香 4階"""

        result = extract_event(text, PUBLISHED, "101")
        event = result["extracted"]

        self.assertEqual(event["title"], "Osaka Street Photography")
        self.assertEqual(event["venue"], "道頓堀 ギャラリー香 4階")
        self.assertEqual(event["prefecture"], "大阪府")
        self.assertEqual(event["start_date"], "2026-08-13")
        self.assertEqual(event["end_date"], "2026-08-18")


    def test_same_event_gets_same_fingerprint_from_different_sources(self):
        first = extract_event(
            "写真展「水の記憶」\n会期: 9月1日～9月6日\n会場: JCIIクラブ25\n東京都千代田区",
            PUBLISHED,
            "200",
        )
        second = extract_event(
            "写真展『水の記憶』\n9月1日〜9月6日\n場所：JCIIクラブ25\n東京で開催します",
            PUBLISHED,
            "201",
        )

        self.assertEqual(first["event_fingerprint"], second["event_fingerprint"])


if __name__ == "__main__":
    unittest.main()
