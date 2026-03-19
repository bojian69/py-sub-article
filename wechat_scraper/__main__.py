"""CLI 入口，支持 python -m wechat_scraper <url> 运行。"""

import argparse
import json
import sys

from wechat_scraper.errors import ScrapeError
from wechat_scraper.parser import Parser
from wechat_scraper.scraper import Scraper
from wechat_scraper.validator import validate_url


def main() -> None:
    parser = argparse.ArgumentParser(
        description="微信公众号文章抓取器 — 从文章链接中提取标题、正文和图片链接",
    )
    parser.add_argument("url", help="微信公众号文章链接")
    parser.add_argument(
        "--cdp-url",
        default="http://127.0.0.1:9222",
        help="Chrome 远程调试地址（默认 http://127.0.0.1:9222）",
    )
    args = parser.parse_args()

    try:
        validated_url = validate_url(args.url)
        scraper = Scraper(cdp_url=args.cdp_url)
        html = scraper.fetch(validated_url)
        article = Parser().parse(html, validated_url)
        print(article.to_json())
    except ScrapeError as exc:
        error_payload = json.dumps(
            {"error_code": exc.error_code, "error_message": exc.error_message},
            ensure_ascii=False,
        )
        print(error_payload, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
