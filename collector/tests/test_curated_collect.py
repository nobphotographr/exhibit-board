import unittest

from collector.curated_collect import build_candidate


class CuratedCollectTests(unittest.TestCase):
    def test_builds_trusted_manual_candidate(self):
        candidate = build_candidate({
            "title": "写真展「光」",
            "host_name": "写真太郎",
            "venue": "写真ギャラリー",
            "address": "東京都中央区1-2-3",
            "prefecture": "東京都",
            "price": "無料",
            "start_date": "2026-08-22",
            "end_date": "2026-08-30",
            "notes": "10:00〜17:00",
            "source": {
                "key": "123",
                "url": "https://x.com/example/status/123",
                "name": "X",
                "author_handle": "example",
            },
        })

        self.assertEqual(candidate["confidence"], 1.0)
        self.assertEqual(candidate["source"]["type"], "manual")
        self.assertEqual(candidate["extracted"]["host_name"], "写真太郎")
        self.assertRegex(candidate["event_fingerprint"], r"^[a-f0-9]{64}$")
        self.assertRegex(candidate["source"]["content_hash"], r"^[a-f0-9]{64}$")

    def test_requires_source_url(self):
        with self.assertRaisesRegex(ValueError, "source requires key and url"):
            build_candidate({
                "title": "写真展",
                "venue": "会場",
                "prefecture": "東京都",
                "start_date": "2026-08-22",
                "end_date": "2026-08-30",
                "source": {"key": "123"},
            })


if __name__ == "__main__":
    unittest.main()
