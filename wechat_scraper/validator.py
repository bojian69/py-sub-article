"""URL 验证模块。"""

from urllib.parse import urlparse, urlunparse

from wechat_scraper.errors import EMPTY_URL, INVALID_URL, ScrapeError


def validate_url(url: str) -> str:
    """
    验证并规范化微信公众号文章 URL。

    Args:
        url: 用户提供的文章链接

    Returns:
        规范化后的 URL 字符串

    Raises:
        ScrapeError: 链接为空或格式不正确时抛出
    """
    if not url:
        raise ScrapeError(EMPTY_URL, "链接不能为空")

    parsed = urlparse(url)

    if parsed.hostname != "mp.weixin.qq.com" or not parsed.path.startswith("/s"):
        raise ScrapeError(INVALID_URL, "链接格式不正确，需要 mp.weixin.qq.com 域名且路径以 /s 开头")

    return urlunparse(parsed)
