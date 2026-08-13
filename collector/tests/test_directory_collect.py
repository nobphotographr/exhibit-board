import unittest
from pathlib import Path

from collector.directory_collect import (
    LocationResolver,
    parse_capa,
    parse_jps_detail,
    parse_jps_index,
    parse_national_photo,
    parse_photo_asahi_detail,
    parse_photo_asahi_listing,
    prefecture_from_text,
)
from collector.photo_culture_collect import already_published


class DirectoryCollectorTests(unittest.TestCase):
    def test_prefecture_inference(self):
        self.assertEqual(prefecture_from_text("東京都港区赤坂"), "東京都")
        self.assertEqual(prefecture_from_text("江東区古石場文化センター"), "東京都")
        self.assertEqual(prefecture_from_text("京都・京都市"), "京都府")

    def test_jps_index_and_table(self):
        index = """<div class="eventBlock"><div class="summary">
          <a href="https://www.jps.gr.jp/?p=1"><h4>展覧会情報8月</h4></a>
          <a href="https://www.jps.gr.jp/?p=1">詳しくはこちら</a>
          </div></div>"""
        self.assertEqual(parse_jps_index(index), ["https://www.jps.gr.jp/?p=1"])
        detail = """<div class="entry-content"><table><tbody>
          <tr><td>会員名</td><td>展覧会名</td><td>開催日</td><td>展覧場所</td></tr>
          <tr><td>山田 太郎</td><td>「海」</td><td>2026/8/20～2026/8/30</td>
          <td>東京都・ギャラリーA</td></tr></tbody></table></div>"""
        candidates = parse_jps_detail(detail, "https://www.jps.gr.jp/?p=1", LocationResolver([]))
        self.assertEqual(candidates[0]["extracted"]["title"], "山田 太郎 「海」")
        self.assertEqual(candidates[0]["extracted"]["prefecture"], "東京都")

    def test_photo_asahi_listing_and_detail(self):
        listing_html = """<div class="box_news"><span class="btn-mini btn-primary">茨城県</span>
          <h3><a href="/event/10/">写真展</a></h3></div>"""
        listing = parse_photo_asahi_listing(listing_html)[0]
        self.assertEqual(listing.prefecture, "茨城県")
        detail = """<div id="leaf"><h2 class="t_main">写真展「森」</h2>
          <div id="leaf_inner"><p>2026年9月4日 ～ 2026年9月10日</p>
          <p id="disp_address">東京都港区赤坂</p><p>【会場】ギャラリー森<br>東京都港区赤坂</p>
          </div><div class="event_date"><p>2026</p><span class="txt_l">09/04</span></div>
          <div class="event_date"><i></i></div>
          <div class="event_date"><p>2026</p><span class="txt_l">09/10</span></div></div>"""
        candidate = parse_photo_asahi_detail(detail, listing.url, listing.prefecture)[0]
        self.assertEqual(candidate["extracted"]["venue"], "ギャラリー森")
        self.assertEqual(candidate["extracted"]["prefecture"], "東京都")
        self.assertEqual(candidate["extracted"]["end_date"], "2026-09-10")

    def test_national_photo_tables(self):
        html = """<figure class="wp-block-table"><table><tbody>
          <tr><td><a href="https://venue.example/">会場A</a><br>住所：東京都港区1-1<br>電話：03</td></tr>
          <tr><td>山田太郎写真展<br>「海」<br>2026年8月20日～8月30日</td></tr>
          </tbody></table><figcaption>会場A</figcaption></figure>"""
        candidate = parse_national_photo(html)[0]
        self.assertEqual(candidate["extracted"]["title"], "山田太郎写真展 「海」")
        self.assertEqual(candidate["extracted"]["address"], "東京都港区1-1")

    def test_capa_venue_sections(self):
        html = """<div class="entry-content"><h2>大阪府</h2><section>
          <div class="place"><h4>Gallery A</h4><ul>
          <li><a href="https://venue.example/">WEBSITE</a></li></ul></div>
          <ul><li><div class="date">8/20～30</div><p>山田太郎「海」<small>(8/24休館)</small></p></li></ul>
          </section></div>"""
        candidate = parse_capa(html, "https://getnavi.jp/capa/exhibition/kinki/")[0]
        self.assertEqual(candidate["extracted"]["venue"], "Gallery A")
        self.assertEqual(candidate["extracted"]["prefecture"], "大阪府")
        self.assertEqual(candidate["extracted"]["start_date"], "2026-08-20")
        self.assertEqual(candidate["extracted"]["title"], "山田太郎「海」")
        self.assertEqual(candidate["extracted"]["notes"], "(8/24休館)")

    def test_cross_directory_duplicate_uses_events_seen_in_same_run(self):
        first = parse_jps_detail(
            """<div class="entry-content"><table><tr>
              <td>佐藤 倫子</td><td>『深濱』</td><td>2026/8/3～2026/8/29</td>
              <td>江東区古石場文化センター 1階展示ロビー</td>
            </tr></table></div>""",
            "https://www.jps.gr.jp/?p=1",
            LocationResolver([]),
        )[0]
        second = parse_capa(
            """<div class="entry-content"><h2>東京都</h2><section>
              <div class="place"><h4>江東区古石場文化センター 1階ロビー</h4>
              <a href="https://venue.example/">WEBSITE</a></div>
              <ul><li><div class="date">8/3～8/29</div><p>佐藤倫子「深濱」</p></li></ul>
            </section></div>""",
            "https://getnavi.jp/capa/exhibition/tokyo/",
        )[0]
        self.assertTrue(already_published(second, [first["extracted"]]))


if __name__ == "__main__":
    unittest.main()
