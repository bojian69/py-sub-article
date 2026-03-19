"""CDP 浏览器抓取模块，通过 Chrome DevTools Protocol 获取渲染后的页面 HTML。"""

import logging
import time

import pychrome

from wechat_scraper.errors import (
    BLOCKED,
    HTTP_ERROR,
    NETWORK_ERROR,
    TIMEOUT,
    ScrapeError,
)

logger = logging.getLogger(__name__)

# 反爬检测关键词
_BLOCKED_KEYWORDS = ("验证码", "verify", "captcha", "频繁", "操作频繁")


class Scraper:
    """通过 CDP 连接本地 Chrome 浏览器，获取渲染后的页面 HTML。"""

    def __init__(self, cdp_url: str = "http://127.0.0.1:9222"):
        """
        初始化 Scraper，指定 CDP 远程调试地址。

        Args:
            cdp_url: Chrome 远程调试端口地址，默认 http://127.0.0.1:9222
        """
        self.cdp_url = cdp_url

    def fetch(self, url: str, timeout: int = 30) -> str:
        """
        通过 CDP 获取页面渲染后的完整 HTML。

        Args:
            url: 已验证的文章 URL
            timeout: 超时时间（秒），默认 30

        Returns:
            渲染后的 HTML 字符串

        Raises:
            ScrapeError: 网络错误、超时、HTTP 错误、反爬拦截等情况
        """
        start_time = time.time()
        logger.info("开始抓取: %s", url)

        try:
            browser = pychrome.Browser(url=self.cdp_url)
        except Exception as exc:
            elapsed = time.time() - start_time
            logger.error("CDP 连接失败 (%.2fs): %s", elapsed, exc)
            raise ScrapeError(NETWORK_ERROR, f"无法连接到 Chrome 浏览器: {exc}") from exc

        tab = None
        try:
            try:
                tab = browser.new_tab()
            except Exception as exc:
                elapsed = time.time() - start_time
                logger.error("创建标签页失败 (%.2fs): %s", elapsed, exc)
                raise ScrapeError(NETWORK_ERROR, f"无法连接到 Chrome 浏览器: {exc}") from exc

            tab.start()

            # Enable Network and Page domains for navigation tracking
            tab.Network.enable()
            tab.Page.enable()

            # Track navigation response status
            response_status = {}

            def _response_received(**kwargs):
                resp = kwargs.get("response", {})
                resp_url = resp.get("url", "")
                # Capture the status of the main document request
                if resp_url and kwargs.get("type") == "Document":
                    response_status["code"] = resp.get("status", 0)

            tab.Network.responseReceived = _response_received

            # Navigate to the URL
            try:
                tab.Page.navigate(url=url, _timeout=timeout)
            except pychrome.TimeoutException as exc:
                elapsed = time.time() - start_time
                logger.error("页面导航超时 (%.2fs): %s", elapsed, url)
                raise ScrapeError(
                    TIMEOUT, f"页面加载超时（{timeout}秒）: {url}"
                ) from exc
            except Exception as exc:
                elapsed = time.time() - start_time
                logger.error("页面导航失败 (%.2fs): %s", elapsed, exc)
                raise ScrapeError(
                    NETWORK_ERROR, f"页面导航失败: {exc}"
                ) from exc

            # Wait for content to be ready (poll instead of waiting for loadEventFired)
            self._wait_for_content(tab, url, timeout, start_time)

            # Check HTTP status code
            status_code = response_status.get("code", 0)
            if status_code and status_code != 200:
                elapsed = time.time() - start_time
                logger.warning(
                    "HTTP 错误 %d (%.2fs): %s", status_code, elapsed, url
                )
                raise ScrapeError(
                    HTTP_ERROR,
                    f"HTTP 请求返回状态码 {status_code}",
                )

            # Extract rendered HTML via JavaScript
            try:
                result = tab.Runtime.evaluate(
                    expression="document.documentElement.outerHTML",
                    _timeout=timeout,
                )
                html = result.get("result", {}).get("value", "")
            except pychrome.TimeoutException as exc:
                elapsed = time.time() - start_time
                logger.error("获取 HTML 超时 (%.2fs): %s", elapsed, url)
                raise ScrapeError(
                    TIMEOUT, f"获取页面内容超时（{timeout}秒）: {url}"
                ) from exc
            except Exception as exc:
                elapsed = time.time() - start_time
                logger.error("获取 HTML 失败 (%.2fs): %s", elapsed, exc)
                raise ScrapeError(
                    NETWORK_ERROR, f"获取页面内容失败: {exc}"
                ) from exc

            # Anti-scraping detection
            self._check_blocked(html)

            elapsed = time.time() - start_time
            logger.info("抓取完成 (%.2fs): %s", elapsed, url)
            return html

        finally:
            if tab is not None:
                try:
                    tab.stop()
                    browser.close_tab(tab)
                except Exception:
                    logger.debug("关闭标签页时出错", exc_info=True)

    @staticmethod
    def _check_blocked(html: str) -> None:
        """
        检测页面是否被反爬机制拦截。

        Args:
            html: 页面 HTML 内容

        Raises:
            ScrapeError: 检测到反爬拦截时抛出 BLOCKED 错误
        """
        html_lower = html.lower()
        for keyword in _BLOCKED_KEYWORDS:
            if keyword in html_lower:
                # Further check: look for verification-related elements
                if any(
                    marker in html_lower
                    for marker in (
                        'id="verify"',
                        'class="verify"',
                        "captcha",
                        "验证码",
                    )
                ):
                    raise ScrapeError(BLOCKED, "页面被反爬机制拦截，需要验证码验证")

        # Check for empty or redirect-only pages
        if not html.strip() or len(html.strip()) < 100:
            raise ScrapeError(BLOCKED, "页面内容异常，可能被反爬机制拦截")

    def _wait_for_content(self, tab, url: str, timeout: int, start_time: float) -> None:
        """
        轮询等待微信文章正文内容加载完成，而非依赖 loadEventFired。

        检测 #js_content 元素出现且有内容即认为页面就绪，
        最多等待 timeout 秒。
        """
        poll_interval = 0.5
        check_script = """
        (function() {
            var el = document.getElementById('js_content');
            if (el && el.innerText && el.innerText.trim().length > 50) return 'ready';
            return 'loading';
        })()
        """
        while True:
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                logger.error("等待页面内容超时 (%.2fs): %s", elapsed, url)
                raise ScrapeError(TIMEOUT, f"页面加载超时（{timeout}秒）: {url}")
            try:
                result = tab.Runtime.evaluate(expression=check_script, _timeout=5)
                status = result.get("result", {}).get("value", "loading")
                if status == "ready":
                    # 额外等待一小段时间让图片 src 属性填充
                    time.sleep(1)
                    return
            except Exception:
                pass
            time.sleep(poll_interval)

