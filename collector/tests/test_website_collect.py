import json
import unittest

from collector.website_collect import (
    annual_festival_parser,
    fujifilm_regional_parser,
    parse_art_gallery_m84,
    parse_canon,
    parse_fuji_photo_gallery_ginza,
    parse_fujifilm,
    parse_gallery_bauhaus,
    parse_gallery_limelight_ics,
    parse_jcii,
    parse_japanese_medium_format_2026,
    parse_kenko,
    parse_leica,
    parse_leofoto,
    parse_ledeco,
    parse_nikon,
    parse_om_system,
    parse_fotori,
    parse_gallery_owada,
    parse_higashikawa,
    parse_house_of_photography,
    parse_ig_photo_gallery,
    parse_iia_gallery,
    parse_irorimura_search,
    parse_fugensha,
    parse_gallery176,
    parse_monography,
    parse_nadar,
    parse_niepce,
    parse_nine_gallery,
    parse_pgi,
    parse_photographers_gallery,
    parse_placem,
    parse_room305,
    parse_red_gallery,
    parse_roonee,
    parse_sirius,
    parse_shadai,
    parse_solaris,
    parse_sony,
    parse_sony_alpha_plaza,
    parse_studio35,
    parse_tosei,
    parse_totem_pole,
    parse_topmuseum,
    parse_zen_foto,
    verified_event_parser,
)


class WebsiteCollectorTests(unittest.TestCase):
    def test_irorimura_photo_search_filters_and_extracts_events(self):
        html = """
          <div class="article-list-item"><div class="article-list-item__body">
            <a class="article-list-item__body-title" href="/articles/131">8/13～ 8/17　写真展『TO2』</a>
            <p class="article-list-item__body-content">写真展『TO2』 会期｜2026年8月13日-8月17日 会場｜イロリムラ プチホール</p>
          </div></div>
          <div class="article-list-item"><div class="article-list-item__body">
            <a class="article-list-item__body-title" href="/articles/102">9/10～ 9/14　Photo Exhibition ヒトとモノ 2026</a>
            <p class="article-list-item__body-content">Photo Exhibition ヒトとモノ 2026 2026/9/10～9/14 [89]画廊 展示室2・3</p>
          </div></div>
          <div class="article-list-item"><div class="article-list-item__body">
            <a class="article-list-item__body-title" href="/articles/art">9/23～ 9/28　絵画展</a>
            <p class="article-list-item__body-content">作家は日常的に写真を撮ります。2026/9/23～9/28</p>
          </div></div>
        """
        candidates = parse_irorimura_search(html)
        self.assertEqual(len(candidates), 2)
        self.assertEqual(candidates[0]["extracted"]["title"], "写真展『TO2』")
        self.assertEqual(candidates[0]["extracted"]["venue"], "イロリムラ プチホール")
        self.assertEqual(candidates[0]["extracted"]["start_date"], "2026-08-13")
        self.assertEqual(candidates[1]["extracted"]["title"], "Photo Exhibition ヒトとモノ 2026")
        self.assertEqual(candidates[1]["extracted"]["end_date"], "2026-09-14")
        self.assertEqual(candidates[1]["extracted"]["venue"], "イロリムラ [89]画廊")

    def test_house_of_photography_metaverse_gallery(self):
        payload = [{
            "date": "2026-07-23T11:57:55",
            "link": "https://houseofphotography-jp.fujifilm.com/contents/gallery/gallery-7434/",
            "title": {"rendered": "【ギャラリー】写真展『光の庭』"},
            "content": {"rendered": """
              <table><tbody>
              <tr><th>開催日時</th><td>
                第一期 2026年8月21日 10:00～2026年8月28日 9:30<br>
                第二期 2026年8月28日 10:00～2026年9月18日 9:30
              </td></tr>
              <tr><th>開催場所</th><td>House of Photography in Metaverse　パノラマギャラリー<br>ENTERから入場</td></tr>
              <tr><th>入場料</th><td>無料</td></tr>
              </tbody></table>
            """},
        }, {
            "date": "2025-12-01T10:00:00",
            "link": "https://houseofphotography-jp.fujifilm.com/contents/gallery/__trashed/",
            "title": {"rendered": "削除済み写真展"},
            "content": {"rendered": "<table><tr><th>開催期間</th><td>2026年1月1日～12月31日</td></tr></table>"},
        }]
        candidates = parse_house_of_photography(json.dumps(payload, ensure_ascii=False))
        self.assertEqual(len(candidates), 1)
        candidate = candidates[0]
        self.assertEqual(candidate["extracted"]["title"], "写真展『光の庭』")
        self.assertEqual(candidate["extracted"]["start_date"], "2026-08-21")
        self.assertEqual(candidate["extracted"]["end_date"], "2026-09-18")
        self.assertEqual(candidate["extracted"]["price"], "無料")
        self.assertEqual(candidate["extracted"]["notes"], "オンライン開催（メタバース）")
        self.assertIn("パノラマギャラリー", candidate["extracted"]["venue"])

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

    def test_fotori_schedule_link(self):
        html = """<div class="entry-content"><p>
          <a href="https://fotori.net/?p=38263">9/23（水）～27（日）餌取 裕也写真展 山岳独行</a>
          <a href="https://fotori.net/?p=1">8/9（日）ワークショップ</a>
        </p></div>"""
        candidate = parse_fotori(html)[0]
        self.assertEqual(candidate["extracted"]["title"], "餌取 裕也写真展 山岳独行")
        self.assertEqual(candidate["extracted"]["end_date"], "2026-09-27")

    def test_shadai_english_cross_year_dates(self):
        html = """<a class="archive_div_a" href="https://example.com/show">
          <div><h3 class="jp">写真術の系譜</h3><p class="en h3">Nov. 20 – Jan. 30, 2027</p></div>
        </a>"""
        candidate = parse_shadai(html)[0]
        self.assertEqual(candidate["extracted"]["start_date"], "2026-11-20")
        self.assertEqual(candidate["extracted"]["end_date"], "2027-01-30")

    def test_placem_schedule_row(self):
        html = """<table><tr><td>2026.08.17 - 2026.08.23</td>
          <td><a href="../schedule/2026/main/test/exhibition.php">君嶋駿「雨のあと」</a></td>
        </tr></table>"""
        candidate = parse_placem(html)[0]
        self.assertEqual(candidate["extracted"]["venue"], "Place M")
        self.assertEqual(candidate["extracted"]["start_date"], "2026-08-17")

    def test_photographers_gallery_card(self):
        html = """<a class="post" href="https://pg-web.net/exhibition/test/">
          <span class="title">岸 幸太 “連荘20”</span><span class="date">2026.8.3 – 2026.8.16</span>
        </a>"""
        candidate = parse_photographers_gallery(html)[0]
        self.assertEqual(candidate["extracted"]["venue"], "photographers’ gallery")

    def test_zen_foto_card(self):
        html = """<article><h3>竹谷出 写真展「よみびとしらず」</h3>
          <p>会期：2026年8月21日（金） — 9月26日（土）</p>
          <a href="/jp/exhibition/test">詳細</a></article>"""
        candidate = parse_zen_foto(html)[0]
        self.assertEqual(candidate["extracted"]["end_date"], "2026-09-26")

    def test_roonee_upcoming_card(self):
        html = """<article class="upcmng"><div><h3>空白の風景</h3><p>Room 1</p>
          <p>会期：2026.08.19 - 2026.08.30</p><a href="https://example.com/show"></a>
        </div></article>"""
        candidate = parse_roonee(html)[0]
        self.assertIn("Room 1", candidate["extracted"]["venue"])

    def test_monography_square_bootstrap_schedule(self):
        repeatable = {"text": {"content": {"quill": {"ops": [{
            "insert": "北井一夫\n「セレクション展」\n2026年8月11日-8月30日\n",
        }]}}}}
        cell = {"content": {"properties": {"repeatables": [repeatable]}}}
        state = {"siteData": {"page": {"properties": {"contentAreas": {
            "userContent": {"content": {"cells": [cell]}},
        }}}}}
        html = f"<script>window.__BOOTSTRAP_STATE__ = {json.dumps(state, ensure_ascii=False)};</script>"
        candidate = parse_monography(html)[0]
        self.assertEqual(candidate["extracted"]["title"], "北井一夫 「セレクション展」")
        self.assertEqual(candidate["extracted"]["end_date"], "2026-08-30")
        self.assertEqual(candidate["extracted"]["venue"], "MONO GRAPHY Camera & Art")

    def test_iia_gallery_home_card(self):
        html = """<div class="item"><div class="item--content">
          <h2 class="item--title">「２Lぐらいがちょうどいい」</h2>
          <div class="item--desc"><p>2026.7.3～10.12</p></div>
          <a href="https://iiagallery.com/exhibition/20260707/">展示詳細</a>
        </div></div>"""
        candidate = parse_iia_gallery(html)[0]
        self.assertEqual(candidate["extracted"]["start_date"], "2026-07-03")
        self.assertEqual(candidate["extracted"]["end_date"], "2026-10-12")
        self.assertEqual(candidate["extracted"]["venue"], "アイアイエーギャラリー")

    def test_red_gallery_schedule_row(self):
        html = """<table><tr><td>2026.08.17 - 2026.08.23</td><td>
          <a href="./schedule/2026/20260817/exhibition.php">小島三幸</a>
          <a href="./schedule/2026/20260817/exhibition.php">11周年記念 メンバー展</a>
        </td></tr></table>"""
        candidate = parse_red_gallery(html)[0]
        self.assertEqual(candidate["extracted"]["end_date"], "2026-08-23")
        self.assertEqual(candidate["extracted"]["title"], "小島三幸 11周年記念 メンバー展")

    def test_sirius_entry_card(self):
        html = """<article class="entry-card"><h3>サコッティ 写真展</h3>
          <p>「あって、ないようなもの」</p><p>2026/08/20 ～ 2026/08/26</p>
          <a href="https://www.photo-sirius.net/tenji/test/">詳しく見る</a></article>"""
        candidate = parse_sirius(html)[0]
        self.assertIn("あって、ないようなもの", candidate["extracted"]["title"])
        self.assertEqual(candidate["extracted"]["end_date"], "2026-08-26")

    def test_niepce_annual_entry(self):
        html = """<div id="content_area"><div class="j-textWithImage">
          2026年9月1日(火)～2026年9月6日(日) 山田太郎 写真展「街」
        </div></div>"""
        candidate = parse_niepce(html)[0]
        self.assertEqual(candidate["extracted"]["title"], "山田太郎 写真展「街」")

    def test_totem_current_and_upcoming(self):
        html = """<main><article class="hentry" id="post-1">
          古佳立「理想と荒野のあいだ」 2026.8.3 – 8.16</article></main>
          <section class="cat-post-widget"><li class="cat-post-item">
          <a href="https://tppg.jp/next/">水島貴大 写真展「雙北青年」2026.8.18 – 8.23</a>
          </li></section>"""
        candidates = parse_totem_pole(html)
        self.assertEqual(len(candidates), 2)
        self.assertEqual(candidates[1]["extracted"]["start_date"], "2026-08-18")

    def test_nadar_excludes_closure(self):
        html = """<div class="post_list"><ul class="panel-group">
          <li><a href="https://g-nadar.net/gallery/260810"><h3 class="ex_title">夏季休業</h3>
          <p>2026年8月10日〜18日</p></a></li>
          <li><a href="https://g-nadar.net/gallery/260819"><h3 class="ex_title">HOLGA EXPO 2026</h3>
          <p>2026年8月19日〜23日</p></a></li></ul></div>"""
        candidates = parse_nadar(html)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["extracted"]["venue"], "Nadar 東京／世田谷")

    def test_nine_gallery_event(self):
        html = """<section class="p-archive--events-bottom">
          <a href="https://ninegallery.com/event/exhibition260811/">
          2026 8月 <h3 class="p-events-loop__item-title">【8/11-16】第13回「勝手にナインギャラリー借りてみた」</h3></a>
        </section>"""
        candidate = parse_nine_gallery(html)[0]
        self.assertEqual(candidate["extracted"]["start_date"], "2026-08-11")
        self.assertTrue(candidate["extracted"]["title"].startswith("第13回"))

    def test_fugensha_exhibition_only(self):
        html = """<section class="events">
          <div class="card item"><a href="https://fugensha.jp/events/show/">
          2026/09/11 （金） - 2026/10/04 （日） 中井菜央 個展「ゆれる水脈」 Exhibition</a></div>
          <div class="card item"><a href="https://example.com/talk">
          2026/09/20 （日） ギャラリートーク Event</a></div></section>"""
        candidates = parse_fugensha(html)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["extracted"]["end_date"], "2026-10-04")

    def test_pgi_current_exhibition(self):
        html = """<div class="ex-current-row"><li class="item">
          <a href="/exhibitions/11324">井津建郎 インド・祈りのこだまする地
          2026.7.22 － 9.16</a></li></div>"""
        candidate = parse_pgi(html)[0]
        self.assertEqual(candidate["extracted"]["title"], "井津建郎 インド・祈りのこだまする地")

    def test_gallery176_upcoming(self):
        html = """<article class="tag-upcoming-exhibitions">
          <h2><a href="https://176.photos/exhibitions/260905/">鈴木郁子写真展「残像の街」</a></h2>
          <p>会期 2026年9月5日(土)〜9月13日(日)</p></article>"""
        candidate = parse_gallery176(html)[0]
        self.assertEqual(candidate["extracted"]["prefecture"], "大阪府")

    def test_studio35_exhibition(self):
        html = """<article class="grid-item category-exhibition">
          <p>2026年9月2日-10月10日</p>
          <a href="https://35fn.com/exhibition/test/">山田太郎 写真展「夜」</a></article>"""
        candidate = parse_studio35(html)[0]
        self.assertEqual(candidate["extracted"]["end_date"], "2026-10-10")

    def test_solaris_skips_closures(self):
        html = """<article class="portfolio_category_44"><div class="portfolio_description">
          <a href="https://solaris-g.com/portfolio_page/260825/">8/25（火）〜8/30（日） 修了展 vol.19</a>
          </div></article><article class="portfolio_category_44"><div class="portfolio_description">
          <a href="https://solaris-g.com/closed/">9/7（月）〜9/14（月） 夏季休廊</a>
          </div></article>"""
        candidates = parse_solaris(html)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["extracted"]["title"], "修了展 vol.19")

    def test_art_gallery_m84_skips_closures_and_tentative_rows(self):
        html = """<div class="entry-content"><table><tbody><tr>
          <td>ベッティナ・ランス写真展『密室』No.12<br>2026.10.05-10.17
          <a href="http://artgallery-m84.com/?attachment_id=1">画像</a></td></tr></tbody>
          <tbody><tr><td>臨時休館<br>2026.09.28-10.04</td></tr></tbody>
          <tbody><tr><td>グループ作品展『仮』<br>2026.11.03-11.08 未定</td></tr></tbody>
          </table></div>"""
        candidates = parse_art_gallery_m84(html)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["extracted"]["end_date"], "2026-10-17")

    def test_ig_photo_gallery_skips_screening(self):
        html = """<center><h4>上映会</h4>8/30<br>
          <a href="exhibition/movie.html">定期上映</a><hr>
          <h4 id="c">9月の企画展</h4>9/8〜26<br>
          <a href="exhibition/ming.html">ジェローム・ミン展「ボールルーム・マケット」</a><hr>
          </center>"""
        candidates = parse_ig_photo_gallery(html)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["extracted"]["start_date"], "2026-09-08")
        self.assertEqual(candidates[0]["source"]["url"], "https://www.igpg.jp/exhibition/ming.html")

    def test_fuji_photo_gallery_ginza_spaces(self):
        html = """<section class="l-container"><div>
          <h2 class="c-heading c-heading-lv3">8月14日(金)〜8月20日(木)</h2>
          <div class="c-grid_item"><ul class="c-imageBox_labels">
          <li>スペース1</li><li>スペース2</li></ul>
          <p class="c-heading c-heading-lv4">第11回 Blue+写真展「海」</p></div>
          </div></section>"""
        candidate = parse_fuji_photo_gallery_ginza(html)[0]
        self.assertEqual(candidate["extracted"]["end_date"], "2026-08-20")
        self.assertIn("スペース1・スペース2", candidate["extracted"]["venue"])

    def test_gallery_limelight_ics_exclusive_end_and_placeholders(self):
        ics = """BEGIN:VCALENDAR
BEGIN:VEVENT
DTSTART;VALUE=DATE:20260816
DTEND;VALUE=DATE:20260823
UID:confirmed@example.com
SUMMARY:額装一展2026
END:VEVENT
BEGIN:VEVENT
DTSTART;VALUE=DATE:20260913
DTEND;VALUE=DATE:20260920
UID:reserved@example.com
SUMMARY:ご予約あり（個展）
END:VEVENT
END:VCALENDAR"""
        candidates = parse_gallery_limelight_ics(ics)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["extracted"]["end_date"], "2026-08-22")

    def test_gallery_bauhaus_schedule(self):
        html = """<main><h1>Now Exhibition</h1><p>gallery bauhaus 20周年記念写真展</p>
          <h2>「Chronicle 時をつなぐ眼差し」</h2>
          <p>会 期 / 2026年6月9日(火)〜9月19日(土) ※2026/8/2〜8/31は夏季休廊</p>
          <a href="https://gallerybauhaus.wixsite.com/website/20260609-chronicle">Read More</a></main>"""
        candidate = parse_gallery_bauhaus(html)[0]
        self.assertEqual(candidate["extracted"]["venue"], "gallery bauhaus")
        self.assertEqual(candidate["extracted"]["end_date"], "2026-09-19")
        self.assertEqual(candidate["extracted"]["notes"], "2026/8/2〜8/31は夏季休廊")
        self.assertEqual(candidate["source"]["url"], "https://gallerybauhaus.wixsite.com/website/20260609-chronicle")

    def test_tosei_current_exhibition(self):
        html = """<table><tr><td class="j12"><p>稲垣徳文写真展 Paris Blue
          2026年8月5日(水) - 8月29日(土)<a href="j_2608_inagaki.html">展示詳細</a></p>
        </td></tr></table>"""
        candidate = parse_tosei(html)[0]
        self.assertEqual(candidate["extracted"]["venue"], "ギャラリー冬青")
        self.assertEqual(candidate["extracted"]["end_date"], "2026-08-29")

    def test_room305_page_json(self):
        page = {"ListItems": [{
            "Guid": "show-1",
            "Description": "公募展『フィルムジャンキーvol.5』\n\n2026.08.19-08.23\nフィルム写真展",
        }]}
        html = f"<script>pageJson : {json.dumps(page, ensure_ascii=False)}, other: true</script>"
        candidate = parse_room305(html)[0]
        self.assertEqual(candidate["extracted"]["title"], "公募展『フィルムジャンキーvol.5』")
        self.assertEqual(candidate["extracted"]["end_date"], "2026-08-23")
        self.assertEqual(candidate["source"]["url"], "https://www.gallery-room305.com/schedule#show-1")

    def test_ledeco_photo_rss_item(self):
        html = """<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"
          xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel><item>
          <title>FOTO.ism 2026夏展「鼓動」</title><link>https://ledeco.net/?p=1</link>
          <category>今週の催事</category><category>４Ｆ</category><category>５Ｆ</category>
          <content:encoded><![CDATA[<p>会期 2026年8月11日～8月16日 写真・映像作品を展示</p>]]></content:encoded>
          </item></channel></rss>"""
        candidate = parse_ledeco(html)[0]
        self.assertEqual(candidate["extracted"]["venue"], "ギャラリー・ルデコ 4F・5F")
        self.assertEqual(candidate["extracted"]["end_date"], "2026-08-16")

    def test_gallery_owada_groups_calendar_days(self):
        html = """<ul class="day-box">
          <li class="day link"><span data-pickup-date="2026-09-9">9</span><ul class="event-list">
          <li><a href="https://shibu-cul.jp/event/1">9/9～13 国産中判フィルム写真展 2026</a></li></ul></li>
          <li class="day link"><span data-pickup-date="2026-09-13">13</span><ul class="event-list">
          <li><a href="https://shibu-cul.jp/event/1">9/9～13 国産中判フィルム写真展 2026【最終日】</a></li></ul></li>
          </ul>"""
        candidate = parse_gallery_owada(html)[0]
        self.assertEqual(candidate["extracted"]["title"], "国産中判フィルム写真展 2026")
        self.assertEqual(candidate["extracted"]["start_date"], "2026-09-09")
        self.assertEqual(candidate["extracted"]["end_date"], "2026-09-13")

    def test_higashikawa_photo_exhibition_only(self):
        html = """<ul><li class="ArticleList__item category-photo-exhibition">
          <div class="ArticleList__title"><a href="https://photo-town.jp/schedule/1">屋外写真展</a></div>
          <p>会期：2026年8月1日～8月31日 場所：東川町文化ギャラリー 今年の展示です。</p>
          </li><li class="ArticleList__item category-event"><div class="ArticleList__title">
          <a href="https://example.com/talk">トーク</a></div></li></ul>"""
        candidates = parse_higashikawa(html)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["extracted"]["venue"], "東川町文化ギャラリー")

    def test_verified_event_requires_marker(self):
        parser = verified_event_parser(
            marker="写真祭2026", title="写真祭2026", venue="市内各所", prefecture="東京都",
            address=None, start_date="2026-10-01", end_date="2026-10-31",
            source_url="https://example.com/", source_name="写真祭",
        )
        self.assertEqual(parser("別のページ"), [])
        self.assertEqual(parser("<h1>写真祭2026</h1>開催" )[0]["extracted"]["start_date"], "2026-10-01")

    def test_japanese_medium_format_osaka_venues(self):
        candidates = parse_japanese_medium_format_2026("<h1>国産中判フィルム写真展2026</h1>")
        self.assertEqual(len(candidates), 2)
        self.assertEqual(candidates[0]["extracted"]["venue"], "rouleur studio")
        self.assertEqual(candidates[1]["extracted"]["venue"], "Gallery ANBAI.")

    def test_annual_festival_uses_current_official_dates(self):
        parser = annual_festival_parser(
            marker="島の写真祭", title_base="島の写真祭", venue="島内各所",
            prefecture="鹿児島県", source_url="https://example.com/", source_name="島の写真祭",
        )
        candidate = parser("<h1>島の写真祭</h1><p>2027年10月12日～10月26日</p>")[0]
        self.assertEqual(candidate["extracted"]["title"], "島の写真祭 2027")
        self.assertEqual(candidate["extracted"]["end_date"], "2027-10-26")


if __name__ == "__main__":
    unittest.main()
