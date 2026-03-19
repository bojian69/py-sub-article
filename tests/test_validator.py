"""URL 验证器测试。"""

import pytest

from wechat_scraper.errors import EMPTY_URL, INVALID_URL, ScrapeError
from wechat_scraper.validator import validate_url


class TestValidateUrl:
    """validate_url 单元测试。"""

    def test_valid_url(self):
        url = "https://mp.weixin.qq.com/s?__biz=MzA3&mid=123&idx=1&sn=abc"
        result = validate_url(url)
        assert "mp.weixin.qq.com" in result

    def test_valid_url_short_form(self):
        url = "https://mp.weixin.qq.com/s/AbCdEfGhIjKlMnOp"
        result = validate_url(url)
        assert result == url

    def test_empty_string_raises(self):
        with pytest.raises(ScrapeError) as exc_info:
            validate_url("")
        assert exc_info.value.error_code == EMPTY_URL

    def test_none_raises(self):
        with pytest.raises(ScrapeError) as exc_info:
            validate_url(None)
        assert exc_info.value.error_code == EMPTY_URL

    def test_wrong_domain_raises(self):
        with pytest.raises(ScrapeError) as exc_info:
            validate_url("https://example.com/s/article")
        assert exc_info.value.error_code == INVALID_URL

    def test_wrong_path_raises(self):
        with pytest.raises(ScrapeError) as exc_info:
            validate_url("https://mp.weixin.qq.com/other/path")
        assert exc_info.value.error_code == INVALID_URL

    def test_no_scheme_raises(self):
        with pytest.raises(ScrapeError) as exc_info:
            validate_url("mp.weixin.qq.com/s/article")
        assert exc_info.value.error_code == INVALID_URL

    def test_http_scheme_accepted(self):
        url = "http://mp.weixin.qq.com/s/article"
        result = validate_url(url)
        assert "mp.weixin.qq.com" in result

    def test_returns_normalized_url(self):
        url = "https://mp.weixin.qq.com/s?__biz=MzA3&mid=123"
        result = validate_url(url)
        assert isinstance(result, str)
        assert len(result) > 0
