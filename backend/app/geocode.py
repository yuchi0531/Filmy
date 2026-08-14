"""国土地理院APIによる住所→座標のジオコーディング。

Filmarks は劇場の座標を返さないため、詳細ページから取得した住所を
国土地理院の AddressSearch API でジオコーディングして緯度経度を得る。

- エンドポイント: ``https://msearch.gsi.go.jp/address-search/AddressSearch?q={住所}``
- レスポンスは GeoJSON Feature の配列。最初の要素の ``geometry.coordinates`` が
  ``[経度, 緯度]``（この順）。戻り値は ``(緯度, 経度)`` の順に正規化する。
"""

from concurrent.futures import ThreadPoolExecutor

import httpx

from app.config import settings

# 国土地理院 AddressSearch API（APIキー不要・日本の住所に高精度）
_GSI_GEOCODE_URL = "https://msearch.gsi.go.jp/address-search/AddressSearch"


def geocode_address(address: str) -> tuple[float, float] | None:
    """住所をジオコーディングし ``(緯度, 経度)`` のタプルで返す。

    空結果・例外・パース失敗は ``None`` を返す（呼び出し側は None を許容する）。
    """
    if not address or not address.strip():
        return None

    try:
        with httpx.Client(
            timeout=httpx.Timeout(5.0),
            headers={"User-Agent": settings.user_agent},
        ) as client:
            response = client.get(_GSI_GEOCODE_URL, params={"q": address.strip()})
            response.raise_for_status()
            features = response.json()
    except (httpx.HTTPError, ValueError, TypeError):
        return None

    if not isinstance(features, list) or not features:
        return None

    # 最初の Feature の geometry.coordinates = [経度, 緯度]
    first = features[0]
    try:
        coords = first["geometry"]["coordinates"]
        longitude, latitude = coords[0], coords[1]
    except (KeyError, TypeError, IndexError, ValueError):
        return None

    try:
        return float(latitude), float(longitude)
    except (TypeError, ValueError):
        return None


def geocode_addresses(addresses: list[str]) -> list[tuple[float, float] | None]:
    """複数住所を並列でジオコーディングし、入力順で結果リストを返す。

    各要素は ``(緯度, 経度)`` または ``None``（失敗）。
    国土地理院APIはレート制限が緩いため、並列実行しても問題ない。
    """
    if not addresses:
        return []

    # 大量住所でもスレッドを枯渇させないよう、同時実行ワーカーを最大3に固定する。
    max_workers = min(len(addresses), 3)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        return list(executor.map(geocode_address, addresses))
