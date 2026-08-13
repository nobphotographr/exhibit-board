import unittest

from collector.website_collect import parse_canon, parse_fujifilm, parse_jcii, parse_sony


class WebsiteCollectorTests(unittest.TestCase):
    def test_fujifilm_card(self):
        html = """<a class="area-link" href="/exhibition/260814_01.html">
          <p class="area-link__title">山田花子写真展「海辺」</p>
          <p class="data-text">2026/08/14（金）～ 2026/08/20（木）</p>
          <p class="data-text data-text--sup">FUJIFILM PHOTO SALON Space1</p>
        </a>"""
        candidates = parse_fujifilm(html)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["extracted"]["start_date"], "2026-08-14")
        self.assertIn("Space1", candidates[0]["extracted"]["venue"])

    def test_canon_card(self):
        html = """<a class="pnl" href="/event/photographyexhibition/gallery/test">
          <div class="title"><span>田中太郎 写真展「森」</span></div>
          <div class="description"><dl><dt>開催期間</dt><dd>2026年9月1日～2026年9月10日</dd></dl>
          <span>大阪</span><span>開催予定</span></div>
        </a>"""
        candidate = parse_canon(html)[0]
        self.assertEqual(candidate["extracted"]["prefecture"], "大阪府")
        self.assertEqual(candidate["extracted"]["venue"], "キヤノンギャラリー大阪")

    def test_sony_card(self):
        html = """<div id="schedule"><ul><li>
          <a href="/camera/imaging-gallery/detail/260904/" aria-label="久井 唯花 作品展 QUALIA">
          <figure><figcaption><span>久井 唯花 作品展 QUALIA</span>
          <span class="data">2026年9月4日(金)～9月17日(木)</span></figcaption></figure></a>
        </li></ul></div>"""
        candidate = parse_sony(html)[0]
        self.assertEqual(candidate["extracted"]["end_date"], "2026-09-17")
        self.assertEqual(candidate["extracted"]["venue"], "Sony Imaging Gallery 銀座")

    def test_jcii_card(self):
        html = """<section class="prepared-exhibition"><div class="item">
          <h3 class="entry-title"><a href="https://example.com/event">佐藤写真展「街」</a></h3>
          <div class="exhibision-description"><span>2026年9月1日(火)</span>〜<span>2026年9月27日(日)</span></div>
        </div></section>"""
        candidate = parse_jcii(html)[0]
        self.assertEqual(candidate["extracted"]["start_date"], "2026-09-01")
        self.assertEqual(candidate["extracted"]["venue"], "JCIIフォトサロン")


if __name__ == "__main__":
    unittest.main()
