"""スクレイピング基底クラス。"""

from abc import ABC, abstractmethod

from bs4 import BeautifulSoup
from lxml import etree

from app.scrapers.exceptions import FilmarksParseError
from app.scrapers.http_client import FilmarksClient
from app.scrapers.parser import check_error_page


class BaseScraper(ABC):
    """Filmarks の「HTML取得 → エラーページ検出 → パース」を担う基底クラス。

    サブクラスは :meth:`parse` を実装する。
    """

    def __init__(self, client: FilmarksClient) -> None:
        self.client = client

    def fetch(self, path: str) -> BeautifulSoup:
        """HTMLを取得して BeautifulSoup にパースし、エラーページを検出して返す。

        - エラーページ（一時的アクセス不可・404相当）は例外に変換される
        - 取得した HTML のパースには ``lxml`` を使用する
        """
        html = self.client.get_html(path)
        try:
            soup = BeautifulSoup(html, "lxml")
        except (etree.XMLSyntaxError, ValueError) as exc:
            raise FilmarksParseError("HTMLのパースに失敗しました。") from exc
        check_error_page(soup)
        return soup

    @abstractmethod
    def parse(self, soup: BeautifulSoup):
        """取得したページをパースして返す。サブクラスで実装する。"""
        raise NotImplementedError
