"""微信公众号文章抓取器公共接口。"""

from wechat_scraper.errors import ScrapeError
from wechat_scraper.models import Article
from wechat_scraper.parser import Parser
from wechat_scraper.scraper import Scraper
from wechat_scraper.validator import validate_url

__all__ = ["Article", "ScrapeError", "Scraper", "Parser", "validate_url", "scrape"]


def scrape(url: str, cdp_url: str = "http://127.0.0.1:9222", timeout: int = 30) -> Article:
    """
    一站式抓取微信公众号文章，返回 Article 对象。

    这是最常用的入口函数，内部依次完成 URL 验证、页面抓取和 HTML 解析。

    Args:
        url: 微信公众号文章链接
        cdp_url: Chrome 远程调试地址，默认 http://127.0.0.1:9222
        timeout: 超时时间（秒），默认 30

    Returns:
        Article 对象，包含 title、content、images、source_url

    Raises:
        ScrapeError: 链接无效、网络错误、超时、反爬拦截、解析失败等

    Example::

        from wechat_scraper import scrape

        article = scrape("https://mp.weixin.qq.com/s/xxxxx")
        print(article.title)
        print(article.images)
        print(article.to_json())
    """
    validated_url = validate_url(url)
    html = Scraper(cdp_url=cdp_url).fetch(validated_url, timeout=timeout)
    return Parser().parse(html, validated_url)
