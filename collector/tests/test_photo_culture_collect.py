import unittest

from collector.photo_culture_collect import (
    already_published,
    parse_article,
    parse_gallery_detail,
    parse_listing_page,
)
from collector.photo_culture_audit import parse_registry
from collector.website_collect import build_candidate


class PhotoCultureCollectorTests(unittest.TestCase):
    def test_gallery_registry(self):
        html = """<table><tr><td>東京都・新宿区</td><td>
          <p><a href="gallerydet.php?i=10">ギャラリーA</a></p>
          <p><a href="gallerydet.php?i=11">ギャラリーB</a></p>
          </td></tr></table>"""
        records = parse_registry(html)
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0].area, "東京都・新宿区")
        self.assertEqual(records[0].detail_url, "https://photoandculture-tokyo.com/gallerydet.php?i=10")

    def test_listing_page(self):
        html = """<div id="contents_set"><figure>
          <a class="cate">京都府</a><a href="contents.php?i=7320">
          <strong class="ah">京都のPURPLEにて、馬場磨貴 個展「DONOR」が開催</strong>
          <span>会期 2026年8月5日（水）～9月6日（日）</span><span>会場 PURPLE</span></a>
          </figure></div>"""
        listing = parse_listing_page(html)[0]
        self.assertEqual(listing.prefecture, "京都府")
        self.assertEqual(listing.venue, "PURPLE")
        self.assertEqual(listing.article_url, "https://photoandculture-tokyo.com/contents.php?i=7320")

    def test_article_uses_structured_title_and_related_link(self):
        html = """<div id="contents_body"><blockquote><ul>
          <li>■展覧会情報</li><li>馬場磨貴 個展「DONOR」</li>
          <li>会期：2026年8月5日～9月6日</li></ul></blockquote>
          <p>関連リンク</p><p><a href="https://purple-purple.com/exhibition/donor/">公式</a></p>
          <div id="exhibision_info"><a class="glink" href="gallerydet.php?i=127">PURPLE</a></div>
          </div>"""
        title, gallery_url, related_url = parse_article(html, "fallback")
        self.assertEqual(title, "馬場磨貴 個展「DONOR」")
        self.assertEqual(gallery_url, "https://photoandculture-tokyo.com/gallerydet.php?i=127")
        self.assertEqual(related_url, "https://purple-purple.com/exhibition/donor/")

    def test_article_ignores_share_links(self):
        html = """<div id="contents_body">
          <blockquote><ul><li>■展覧会情報</li><li>写真展「海」</li></ul></blockquote>
          <p>【関連リンク】</p><p><a href="https://venue.example/exhibitions/sea">公式</a></p>
          <div id="exhibision_info"><a class="glink" href="gallerydet.php?i=1">会場</a></div>
          <div><a href="https://social-plugins.line.me/lineit/share?url=x">share</a></div>
          </div>"""
        _, _, related_url = parse_article(html, "fallback")
        self.assertEqual(related_url, "https://venue.example/exhibitions/sea")

    def test_article_combines_generic_series_with_exhibition_title(self):
        html = """<div id="contents_body"><blockquote><ul>
          <li>■展覧会情報</li><li>GRAPHGATE企画展</li>
          <li>水島貴大「環島回憶錄」</li><li>［東京展］</li>
          <li>会期：2026年9月1日～9月5日</li></ul></blockquote>
          </div>"""
        title, _, _ = parse_article(html, "fallback")
        self.assertEqual(title, "GRAPHGATE企画展 水島貴大「環島回憶錄」")

    def test_gallery_detail(self):
        html = """<div id="dleft_blk"><ul>
          <li><p class="dt">住所</p><p>〒604-8261 京都府京都市中京区式阿弥町122-1</p></li>
          <li><p class="dt">URL</p><p><a href="https://purple-purple.com/">公式</a></p></li>
          </ul></div>"""
        address, official = parse_gallery_detail(html)
        self.assertEqual(address, "京都府京都市中京区式阿弥町122-1")
        self.assertEqual(official, "https://purple-purple.com/")

    def test_duplicate_matches_same_dates_and_venue(self):
        candidate = build_candidate(
            title="写真展「海」", venue="ニコンプラザ東京 ニコンサロン", prefecture="東京都",
            start_date="2026-09-01", end_date="2026-09-10", source_url="https://example.com/e",
            source_name="test", card_text="test",
        )
        published = [{
            "title": "山田太郎 写真展「海」", "venue": "ニコンサロン",
            "start_date": "2026-09-01", "end_date": "2026-09-10",
        }]
        self.assertTrue(already_published(candidate, published))

    def test_duplicate_normalizes_brand_and_exhibition_words(self):
        candidate = build_candidate(
            title="宇井眞紀子『ankoraci』", venue="キャノンギャラリーS", prefecture="東京都",
            start_date="2026-08-17", end_date="2026-09-29", source_url="https://example.com/e",
            source_name="test", card_text="test",
        )
        published = [{
            "title": "宇井眞紀子 写真展『ankoraci』", "venue": "キヤノンギャラリーS",
            "start_date": "2026-08-17", "end_date": "2026-09-29",
        }]
        self.assertTrue(already_published(candidate, published))


if __name__ == "__main__":
    unittest.main()
