import json
import unittest

from collector.website_collect import (
    fujifilm_regional_parser,
    parse_canon,
    parse_fujifilm,
    parse_jcii,
    parse_kenko,
    parse_leica,
    parse_leofoto,
    parse_nikon,
    parse_om_system,
    parse_sony,
    parse_sony_alpha_plaza,
    parse_topmuseum,
)


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

    def test_fujifilm_regional_card(self):
        parser = fujifilm_regional_parser(
            venue="富士フイルムフォトサロン 大阪", prefecture="大阪府",
            address="大阪府大阪市中央区本町2-5-7", base_url="https://example.com/osaka/",
        )
        html = """<div id="nowevent_list"><div class="nowevent"><div class="salonbox">
          <h4><a href="26082101.html">JPS新入会員展「私の仕事」</a></h4>
          <p class="exdate">開催期間：2026年8月21日（金）～8月27日（木）</p>
        </div></div></div>"""
        candidate = parser(html)[0]
        self.assertEqual(candidate["extracted"]["end_date"], "2026-08-27")
        self.assertEqual(candidate["source"]["url"], "https://example.com/osaka/26082101.html")

    def test_sony_alpha_plaza_gallery_only(self):
        data = {"EventInformationList": [{
            "RefineClassification__c": "ギャラリー", "Place__c": "札幌",
            "SubTitle__c": "写真家 野口純一 作品展", "Name__c": "TRIBUTE",
            "StartTime__c": "2026-08-22 11:00:00", "EndTime__c": "2026-09-03 16:00:00",
            "URL__c": "https%3A%2F%2Fexample.com%2Fevent",
        }, {
            "RefineClassification__c": "トークショー", "Place__c": "札幌",
        }]}
        candidate = parse_sony_alpha_plaza(f"callback({json.dumps(data, ensure_ascii=False)})")[0]
        self.assertEqual(candidate["extracted"]["venue"], "αプラザ札幌")
        self.assertEqual(candidate["source"]["url"], "https://example.com/event")

    def test_nikon_card(self):
        html = """<li class="item-event"><a class="item-inner" href="/event/test.html">
          <div class="icon-wrap"><span class="icon">ニコンプラザ大阪 THE GALLERY</span></div>
          <p class="is-title is-name"><span>山田太郎</span><span>青い街</span></p>
          <time class="day" data-start="2026/09/01 00:00" data-end="2026/09/14 23:59"></time>
        </a></li>"""
        candidate = parse_nikon(html)[0]
        self.assertEqual(candidate["extracted"]["prefecture"], "大阪府")
        self.assertEqual(candidate["extracted"]["start_date"], "2026-09-01")

    def test_leica_japan_gallery(self):
        html = """<div class="node--events-overview">
          <div class="card_headline_info__headline">写真展「what matters」</div>
          <div class="card__event-info__item">2026/08/01 - 2026/10/01</div>
          <div class="card__event-info__item">日本</div>
          <div class="card__event-info__item">Leica Gallery Kyoto</div>
          <a href="/ja-JP/event/test">詳細</a></div>"""
        candidate = parse_leica(html)[0]
        self.assertEqual(candidate["extracted"]["venue"], "ライカギャラリー京都")
        self.assertEqual(candidate["extracted"]["end_date"], "2026-10-01")

    def test_kenko_card(self):
        html = """<section class="gal-02"><ul class="gal-list"><li class="clickable">
          <h3 class="name">子どもの写真展</h3><p class="date">2026年8月14日～8月24日</p>
          <a class="bt" href="/gallery/test.html">詳細</a></li></ul></section>"""
        candidate = parse_kenko(html)[0]
        self.assertEqual(candidate["extracted"]["venue"], "ケンコー・トキナーギャラリー")

    def test_topmuseum_exhibition_room_only(self):
        html = """<div class="slider__item"><a href="/exhibition/123/">
          <dl><dt><em class="main">TOPコレクション</em><em class="sub">明日の食卓</em></dt>
          <dd><em>3F 展示室</em>2026.7.2（木）～ 2026.9.21（月）</dd></dl></a></div>
          <div class="slider__item"><a href="/movie/1"><dl><dt><em class="main">映画</em></dt>
          <dd><em>1F ホール</em>2026.8.1～2026.8.2</dd></dl></a></div>"""
        candidates = parse_topmuseum(html)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["extracted"]["end_date"], "2026-09-21")

    def test_om_system_note_cards(self):
        html = r'''\"href\":\"https://note.com/omsystem_plaza/n/n123?magazine_key=m1\",\"title\":\"2026年8月20日（木）～8月31日（月）木村琢磨 写真展「形而上下」\"'''
        candidate = parse_om_system(html)[0]
        self.assertEqual(candidate["extracted"]["title"], "木村琢磨 写真展「形而上下」")
        self.assertEqual(candidate["extracted"]["end_date"], "2026-08-31")

    def test_leofoto_wordpress_posts(self):
        posts = [{
            "date": "2026-07-25T10:04:31", "link": "https://leofoto.co.jp/event/1",
            "title": {"rendered": "【イベント情報】9/9(水)~ 写真家 田村拓也氏写真展開催のお知らせ"},
            "content": {"rendered": "<p>9/9(水）～9/27(日）にショールームにて写真展を開催します。</p>"},
        }]
        candidate = parse_leofoto(json.dumps(posts, ensure_ascii=False))[0]
        self.assertEqual(candidate["extracted"]["start_date"], "2026-09-09")
        self.assertEqual(candidate["extracted"]["prefecture"], "埼玉県")


if __name__ == "__main__":
    unittest.main()
