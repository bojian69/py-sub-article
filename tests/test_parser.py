"""Unit tests for the Parser class."""

import pytest

from wechat_scraper.errors import NO_CONTENT, ScrapeError
from wechat_scraper.parser import Parser


@pytest.fixture
def parser():
    return Parser()


def _wrap_html(body: str) -> str:
    """Wrap body content in a minimal HTML document."""
    return f"<html><head></head><body>{body}</body></html>"


# --- Title extraction ---

class TestExtractTitle:
    def test_title_from_activity_name(self, parser):
        html = _wrap_html('<h2 id="activity-name">测试标题</h2>')
        article = parser.parse(
            _wrap_html(
                '<h2 id="activity-name">测试标题</h2>'
                '<div id="js_content"><p>正文内容</p></div>'
            ),
            "https://mp.weixin.qq.com/s/test",
        )
        assert article.title == "测试标题"

    def test_title_from_h1_rich_media_title(self, parser):
        article = parser.parse(
            _wrap_html(
                '<h1 class="rich_media_title">另一个标题</h1>'
                '<div id="js_content"><p>正文内容</p></div>'
            ),
            "https://mp.weixin.qq.com/s/test",
        )
        assert article.title == "另一个标题"

    def test_activity_name_takes_priority(self, parser):
        article = parser.parse(
            _wrap_html(
                '<h2 id="activity-name">优先标题</h2>'
                '<h1 class="rich_media_title">备选标题</h1>'
                '<div id="js_content"><p>正文内容</p></div>'
            ),
            "https://mp.weixin.qq.com/s/test",
        )
        assert article.title == "优先标题"

    def test_missing_title_returns_empty_string(self, parser):
        article = parser.parse(
            _wrap_html('<div id="js_content"><p>正文内容</p></div>'),
            "https://mp.weixin.qq.com/s/test",
        )
        assert article.title == ""


    def test_title_with_whitespace_is_stripped(self, parser):
        article = parser.parse(
            _wrap_html(
                '<h2 id="activity-name">  空格标题  </h2>'
                '<div id="js_content"><p>正文内容</p></div>'
            ),
            "https://mp.weixin.qq.com/s/test",
        )
        assert article.title == "空格标题"


# --- Content extraction ---

class TestExtractContent:
    def test_content_from_js_content(self, parser):
        article = parser.parse(
            _wrap_html('<div id="js_content"><p>段落一</p><p>段落二</p></div>'),
            "https://mp.weixin.qq.com/s/test",
        )
        assert "段落一" in article.content
        assert "段落二" in article.content

    def test_content_from_rich_media_content(self, parser):
        article = parser.parse(
            _wrap_html('<div class="rich_media_content"><p>备选正文</p></div>'),
            "https://mp.weixin.qq.com/s/test",
        )
        assert "备选正文" in article.content

    def test_paragraph_separation_preserved(self, parser):
        article = parser.parse(
            _wrap_html(
                '<div id="js_content"><p>第一段</p><p>第二段</p><p>第三段</p></div>'
            ),
            "https://mp.weixin.qq.com/s/test",
        )
        lines = article.content.split("\n")
        assert len(lines) >= 3
        assert "第一段" in lines[0]
        assert "第二段" in lines[1]
        assert "第三段" in lines[2]

    def test_script_and_style_removed(self, parser):
        article = parser.parse(
            _wrap_html(
                '<div id="js_content">'
                "<script>alert('xss')</script>"
                "<style>.hidden{display:none}</style>"
                "<p>干净的正文</p>"
                "</div>"
            ),
            "https://mp.weixin.qq.com/s/test",
        )
        assert "alert" not in article.content
        assert "script" not in article.content.lower()
        assert "style" not in article.content.lower()
        assert "display" not in article.content
        assert "干净的正文" in article.content

    def test_html_tags_stripped(self, parser):
        article = parser.parse(
            _wrap_html(
                '<div id="js_content"><p><strong>加粗</strong>和<em>斜体</em></p></div>'
            ),
            "https://mp.weixin.qq.com/s/test",
        )
        assert "<strong>" not in article.content
        assert "<em>" not in article.content
        assert "加粗" in article.content
        assert "斜体" in article.content

    def test_missing_content_raises_scrape_error(self, parser):
        with pytest.raises(ScrapeError) as exc_info:
            parser.parse(
                _wrap_html("<div>没有正文容器</div>"),
                "https://mp.weixin.qq.com/s/test",
            )
        assert exc_info.value.error_code == NO_CONTENT


    def test_empty_content_container_raises_scrape_error(self, parser):
        with pytest.raises(ScrapeError) as exc_info:
            parser.parse(
                _wrap_html('<div id="js_content"></div>'),
                "https://mp.weixin.qq.com/s/test",
            )
        assert exc_info.value.error_code == NO_CONTENT


# --- Image extraction ---

class TestExtractImages:
    def test_images_from_data_src(self, parser):
        article = parser.parse(
            _wrap_html(
                '<div id="js_content">'
                '<p>正文</p>'
                '<img data-src="https://img.example.com/1.jpg" src="https://placeholder.com/p.gif">'
                "</div>"
            ),
            "https://mp.weixin.qq.com/s/test",
        )
        assert article.images == ["https://img.example.com/1.jpg"]

    def test_images_fallback_to_src(self, parser):
        article = parser.parse(
            _wrap_html(
                '<div id="js_content">'
                '<p>正文</p>'
                '<img src="https://img.example.com/2.jpg">'
                "</div>"
            ),
            "https://mp.weixin.qq.com/s/test",
        )
        assert article.images == ["https://img.example.com/2.jpg"]

    def test_data_src_priority_over_src(self, parser):
        article = parser.parse(
            _wrap_html(
                '<div id="js_content">'
                '<p>正文</p>'
                '<img data-src="https://real.com/img.jpg" src="https://lazy.com/placeholder.gif">'
                "</div>"
            ),
            "https://mp.weixin.qq.com/s/test",
        )
        assert article.images == ["https://real.com/img.jpg"]

    def test_image_order_preserved(self, parser):
        article = parser.parse(
            _wrap_html(
                '<div id="js_content">'
                '<p>正文</p>'
                '<img data-src="https://img.com/a.jpg">'
                '<img data-src="https://img.com/b.jpg">'
                '<img data-src="https://img.com/c.jpg">'
                "</div>"
            ),
            "https://mp.weixin.qq.com/s/test",
        )
        assert article.images == [
            "https://img.com/a.jpg",
            "https://img.com/b.jpg",
            "https://img.com/c.jpg",
        ]

    def test_small_image_filtered_by_width(self, parser):
        article = parser.parse(
            _wrap_html(
                '<div id="js_content">'
                '<p>正文</p>'
                '<img data-src="https://img.com/small.jpg" width="1">'
                '<img data-src="https://img.com/normal.jpg" width="100">'
                "</div>"
            ),
            "https://mp.weixin.qq.com/s/test",
        )
        assert article.images == ["https://img.com/normal.jpg"]

    def test_small_image_filtered_by_height(self, parser):
        article = parser.parse(
            _wrap_html(
                '<div id="js_content">'
                '<p>正文</p>'
                '<img data-src="https://img.com/tracker.gif" height="1">'
                '<img data-src="https://img.com/photo.jpg" height="200">'
                "</div>"
            ),
            "https://mp.weixin.qq.com/s/test",
        )
        assert article.images == ["https://img.com/photo.jpg"]

    def test_small_image_filtered_at_boundary(self, parser):
        """Images with width or height < 10 are filtered; 10 is kept."""
        article = parser.parse(
            _wrap_html(
                '<div id="js_content">'
                '<p>正文</p>'
                '<img data-src="https://img.com/nine.jpg" width="9">'
                '<img data-src="https://img.com/ten.jpg" width="10">'
                "</div>"
            ),
            "https://mp.weixin.qq.com/s/test",
        )
        assert article.images == ["https://img.com/ten.jpg"]

    def test_empty_image_list_when_no_images(self, parser):
        article = parser.parse(
            _wrap_html('<div id="js_content"><p>纯文本正文</p></div>'),
            "https://mp.weixin.qq.com/s/test",
        )
        assert article.images == []

    def test_img_without_src_or_data_src_skipped(self, parser):
        article = parser.parse(
            _wrap_html(
                '<div id="js_content">'
                '<p>正文</p>'
                "<img alt='no url'>"
                "</div>"
            ),
            "https://mp.weixin.qq.com/s/test",
        )
        assert article.images == []


# --- parse() integration ---

class TestParse:
    def test_parse_returns_article_with_source_url(self, parser):
        url = "https://mp.weixin.qq.com/s/abc123"
        article = parser.parse(
            _wrap_html(
                '<h2 id="activity-name">标题</h2>'
                '<div id="js_content"><p>正文</p></div>'
            ),
            url,
        )
        assert article.source_url == url

    def test_parse_full_article(self, parser):
        article = parser.parse(
            _wrap_html(
                '<h2 id="activity-name">完整文章</h2>'
                '<div id="js_content">'
                "<p>第一段</p>"
                "<p>第二段</p>"
                '<img data-src="https://img.com/photo.jpg">'
                "</div>"
            ),
            "https://mp.weixin.qq.com/s/full",
        )
        assert article.title == "完整文章"
        assert "第一段" in article.content
        assert "第二段" in article.content
        assert article.images == ["https://img.com/photo.jpg"]
        assert article.source_url == "https://mp.weixin.qq.com/s/full"
