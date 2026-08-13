"""テスト用のモック HTML / JSON フィクスチャ。

実際の Filmarks の HTML 構造（app/scrapers のセレクタ）に合わせた
スタティックなマークアップを提供する。ネットワークアクセスは一切しない。
"""

# --- 一覧ページ（/list/* , /search） ---

# 1枚の映画カード。data-mark / data-clip はカード自体の属性（JSON）。
_CARD_HTML = """
<div class="js-cassette"
     data-mark='{{"active": true, "movie_id": {movie_id}, "id": {movie_id}, "count": {mark}}}'
     data-clip='{{"active": true, "movie_id": {movie_id}, "id": {movie_id}, "count": {clip}}}'>
  <a href="/movies/{movie_id}">
    <h3 class="p-content-cassette__title">{title}</h3>
  </a>
  <div class="c-rating__score">{rating}</div>
  <div class="c2-poster-m"><img src="{poster}" alt=""></div>
  <h4 class="p-content-cassette__other-info-title">上映日：</h4>
  <span>{release}</span>
  <ul class="genres"><li><a href="/genre/drama">ドラマ</a></li><li><a href="/genre/sf">SF</a></li></ul>
</div>
"""

# 映画IDを持たないカード（パースでスキップされる）。
_CARD_NO_ID_HTML = """
<div class="js-cassette">
  <a href="/other">IDなしカード</a>
  <h3 class="p-content-cassette__title">除去される</h3>
</div>
"""


def list_page_html(heading: str = "上映中の最新映画 459作品") -> str:
    """映画一覧ページの HTML（2枚の通常カード＋1枚のIDなしカード）。"""
    cards = (
        _CARD_HTML.format(
            movie_id=1001,
            title="テスト映画A",
            rating="3.5",
            poster="https://img.example.test/a.jpg",
            mark=500,
            clip=120,
            release="2026年08月01日",
        )
        + _CARD_HTML.format(
            movie_id=1002,
            title="テスト映画B",
            rating="",
            poster="https://img.example.test/b.jpg",
            mark=0,
            clip=0,
            release="2026年08月08日",
        )
        + _CARD_NO_ID_HTML
    )
    return (
        '<html><body><h1 class="c-heading-1">'
        + heading
        + "</h1><div class='p-contents-grid'>"
        + cards
        + "</div></body></html>"
    )


def empty_list_page_html() -> str:
    """映画カードが1つも無い一覧ページ（空結果）。"""
    return (
        '<html><body><h1 class="c-heading-1">上映中の最新映画 0作品</h1>'
        '<div class="p-contents-grid"></div></body></html>'
    )


LIST_PAGE_HTML = list_page_html()
SEARCH_PAGE_HTML = (
    '<html><body><h1 class="c-heading-1">テストに関する映画 3作品</h1>'
    '<div class="p-contents-grid">'
    + _CARD_HTML.format(
        movie_id=2001,
        title="検索結果映画",
        rating="4.0",
        poster="https://img.example.test/s.jpg",
        mark=99,
        clip=7,
        release="2026年09月01日",
    )
    + "</div></body></html>"
)

# --- 映画詳細ページ（/movies/{id}） ---

DETAIL_PAGE_HTML = """
<html><head>
<link rel="canonical" href="https://filmarks.com/movies/1001">
</head><body>
<h2 class="p-content-detail__title"><span>テスト映画A</span></h2>
<p class="p-content-detail__original">TEST MOVIE A</p>
<div id="js-content-detail-synopsis">
  <content-detail-synopsis :outline="&quot;これはあらすじです。&quot;"></content-detail-synopsis>
</div>
<div class="c2-rating-l__text">3.5</div>
<div class="c2-poster-l"><img src="https://img.example.test/a.jpg" alt=""></div>
<div class="js-btn-mark" data-mark='{"active":true,"movie_id":1001,"id":1001,"count":500}'></div>
<div class="js-btn-clip" data-clip='{"active":true,"movie_id":1001,"id":1001,"count":120}'></div>
<h3 class="p-content-detail__primary-info-title">上映日：2026年08月01日</h3>
<h3 class="p-content-detail__primary-info-title">上映時間：120分</h3>
<h3 class="p-content-detail__primary-info-title">ジャンル</h3>
<ul><li><a href="#">SF</a></li><li><a href="#">ドラマ</a></li></ul>
<h3 class="p-content-detail__primary-info-title">監督</h3>
<ul><li><a href="#">山田監督</a></li></ul>
<div class="p-people-list__casts">
  <h4 class="p-people-list__item">
    <div class="c2-button-tertiary-s-multi-text__text">主演俳優</div>
    <div class="c2-button-tertiary-s-multi-text__subtext">主人公役</div>
  </h4>
  <h4 class="p-people-list__item">脇役俳優</h4>
</div>
<li class="p-content-detail-links__item--official"><a href="https://www.example.test/official">公式サイト</a></li>
<script type="application/ld+json">{"@type":"Movie","url":"https://filmarks.com/movies/1001","name":"テスト映画A","outline":"これはあらすじです。","duration":"PT120M","datePublished":"2026-08-01","aggregateRating":{"ratingValue":3.5,"reviewCount":42}}</script>
</body></html>
"""

# 配信（VOD）情報を描画する詳細ページ（構造が揃った際の回帰防止用）。
_VOD_BLOCK_HTML = """
<div class="c2-list-vod">
  <div class="js-btn-vod" data-service="U-NEXT" data-type="見放題">U-NEXT</div>
  <li class="js-btn-vod" data-service="Amazon Prime Video" data-type="見放題">アマプラ</li>
</div>
"""
STREAMING_PAGE_HTML = DETAIL_PAGE_HTML.replace(
    "</body>", _VOD_BLOCK_HTML + "</body>"
)

# --- エラーページ ---

# 一時的アクセス不可
UNAVAILABLE_PAGE_HTML = (
    '<html><body><p class="main__text">一時的にアクセスできない状態です。時間をおいて再度お試しください。</p></body></html>'
)

# 404相当
NOT_FOUND_PAGE_HTML = (
    '<html><body><p class="main__status-ja">お探しのページは見つかりません。</p></body></html>'
)

# 正常（エラーテキスト無し）
NORMAL_PAGE_HTML = '<html><body><h1 class="c-heading-1">通常ページ</h1></body></html>'

# --- 劇場系 ---

# 都道府県ページ（エリア選択リンクのみ）
THEATER_PREF_HTML = """
<html><head>
<script type="application/ld+json">{"@type":"BreadcrumbList","itemListElement":[{"item":{"name":"東京都の映画館"}}]}</script>
</head><body>
<h1 class="c-heading-1">東京都の映画館：上映中・上映予定の映画館を探す</h1>
<a class="p-content-schedule-select-item__link" href="/theaters/tokyo/99">新宿(4)</a>
<a class="p-content-schedule-select-item__link" href="/theaters/tokyo/134">有楽町(3)</a>
</body></html>
"""

# エリアページ（劇場カード）
THEATER_AREA_HTML = """
<html><head>
<script type="application/ld+json">{"@type":"BreadcrumbList","itemListElement":[{"item":{"name":"東京都の映画館"}}]}</script>
</head><body>
<h1 class="c-heading-1">新宿の映画館</h1>
<div class="p-theater-card__theater js-theater-card" data-theater-id="172">
  <a href="/theaters/tokyo/99/172"><h3 class="p-theater-card__theater-name">テストシネマ新宿</h3></a>
</div>
<div class="p-theater-card__theater js-theater-card" data-theater-id="173">
  <a href="/theaters/tokyo/99/173"><h3 class="p-theater-card__theater-name">テストシネマ新宿二番館</h3></a>
</div>
</body></html>
"""

# 劇場詳細ページ（静止HTML部分）
THEATER_DETAIL_HTML = """
<html><head>
<script type="application/ld+json">{"@type":"BreadcrumbList","itemListElement":[{"item":{"name":"東京都の映画館"}}]}</script>
</head><body>
<div class="p-theater-movies-info__name">テストシネマ新宿</div>
<div class="p-theater-movies-info__address">東京都新宿区新宿3-1-1</div>
<a class="p-theater-movies-info__map" href="https://maps.google.com/?q=テストシネマ新宿">地図を見る</a>
</body></html>
"""

# 劇場スケジュールJSON（/pia_theaters/{id}/movies?schedule_date=...）
SCHEDULE_JSON = """{
  "movies": [
    {
      "id": 3001,
      "title": "スケジュール映画",
      "imagePath": "https://img.example.test/sched.jpg",
      "screens": [
        {
          "screenFormat": "IMAX",
          "showtimes": [
            {"start": "2026-08-14T10:00:00+09:00", "end": "2026-08-14T12:00:00+09:00"},
            {"start": "2026-08-14T13:30:00+09:00", "end": "2026-08-14T15:30:00+09:00"}
          ]
        }
      ]
    }
  ]
}"""

# 近隣劇場JSON（/pia_theaters?latitude=...&longitude=...&radius=...）
NEARBY_JSON = """{
  "piaTheaters": [
    {"id": "172", "name": "テストシネマ新宿", "url": "/theaters/tokyo/99/172"},
    {"id": "200", "name": "テストシネマ渋谷", "url": "/theaters/tokyo/88/200"}
  ]
}"""