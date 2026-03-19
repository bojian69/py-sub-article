"""HTML 解析模块，从微信公众号文章 HTML 中提取结构化数据。"""

import re
from datetime import datetime, timezone, timedelta

from bs4 import BeautifulSoup, Tag

from wechat_scraper.errors import NO_CONTENT, ScrapeError
from wechat_scraper.models import Article


class Parser:
    """微信公众号文章 HTML 解析器。"""

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """提取文章标题，未找到时返回空字符串。"""
        el = soup.select_one("#activity-name")
        if el is None:
            el = soup.select_one("h1.rich_media_title")
        if el is None:
            return ""
        return el.get_text(strip=True)

    def _extract_content(self, soup: BeautifulSoup) -> str:
        """提取文章正文纯文本，保留段落分隔。"""
        container = soup.select_one("#js_content")
        if container is None:
            container = soup.select_one(".rich_media_content")
        if container is None:
            return ""

        # Remove script and style elements
        for tag in container.find_all(["script", "style"]):
            tag.decompose()

        # Collect text from block-level elements to preserve paragraph separation
        paragraphs: list[str] = []
        block_tags = {"p", "div", "section", "blockquote", "h1", "h2", "h3", "h4", "h5", "h6", "li", "br"}

        def _walk(node: Tag) -> None:
            for child in node.children:
                if isinstance(child, Tag):
                    if child.name in block_tags:
                        text = child.get_text(strip=True)
                        if text:
                            paragraphs.append(text)
                    else:
                        _walk(child)
                else:
                    text = child.strip()
                    if text:
                        paragraphs.append(text)

        _walk(container)

        if not paragraphs:
            # Fallback: get all text from container
            text = container.get_text(separator="\n", strip=True)
            return text

        return "\n".join(paragraphs)

    def _extract_images(self, soup: BeautifulSoup) -> list[str]:
        """提取文章正文区域中的图片链接，过滤小尺寸图片。"""
        container = soup.select_one("#js_content")
        if container is None:
            container = soup.select_one(".rich_media_content")
        if container is None:
            return []

        images: list[str] = []
        for img in container.find_all("img"):
            # Filter small images (width or height < 10)
            if self._is_small_image(img):
                continue

            url = img.get("data-src") or img.get("src")
            if url:
                images.append(url)

        return images

    @staticmethod
    def _is_small_image(img: Tag) -> bool:
        """Check if an image is too small (width or height < 10 pixels)."""
        for attr in ("width", "height"):
            val = img.get(attr)
            if val is not None:
                try:
                    num = float(re.sub(r"[^\d.]", "", str(val)))
                    if num < 10:
                        return True
                except (ValueError, TypeError):
                    pass
        return False

    def _extract_author(self, soup: BeautifulSoup) -> str:
        """提取文章作者（公众号名称），未找到返回空字符串。"""
        el = soup.select_one("#js_name")
        if el:
            return el.get_text(strip=True)
        # 备选：从 JS 变量中提取 nick_name
        script_text = soup.get_text()
        m = re.search(r"nick_name:\s*JsDecode\('([^']+)'\)", script_text)
        if m:
            return m.group(1)
        return ""

    def _extract_publish_time(self, soup: BeautifulSoup) -> str:
        """提取发布时间，优先从 var ct 时间戳提取，格式化为可读字符串。"""
        # 从 #publish_time 元素提取（JS 渲染后可能有值）
        el = soup.select_one("#publish_time")
        if el:
            text = el.get_text(strip=True)
            if text:
                return text

        # 从 JS 变量 var ct = "timestamp" 提取
        for script in soup.find_all("script"):
            if script.string and "var ct" in script.string:
                m = re.search(r'var\s+ct\s*=\s*"(\d+)"', script.string)
                if m:
                    ts = int(m.group(1))
                    cst = timezone(timedelta(hours=8))
                    dt = datetime.fromtimestamp(ts, tz=cst)
                    return dt.strftime("%Y年%m月%d日 %H:%M")
        return ""

    def parse(self, html: str, source_url: str) -> Article:
        """
        解析 HTML 提取文章数据。

        Args:
            html: 渲染后的完整 HTML
            source_url: 文章原始 URL

        Returns:
            Article 对象

        Raises:
            ScrapeError: 未找到文章正文内容时抛出
        """
        soup = BeautifulSoup(html, "lxml")

        title = self._extract_title(soup)
        content = self._extract_content(soup)
        images = self._extract_images(soup)
        author = self._extract_author(soup)
        publish_time = self._extract_publish_time(soup)

        if not content:
            raise ScrapeError(NO_CONTENT, "未找到文章正文内容")

        # 封面图：正文中第二张图片
        cover_image = images[1] if len(images) > 1 else (images[0] if images else "")

        return Article(
            title=title,
            content=content,
            images=images,
            cover_image=cover_image,
            author=author,
            publish_time=publish_time,
            source_url=source_url,
        )
