"""HTTP API 服务器模块。"""

import logging
from dataclasses import asdict

from flask import Flask, jsonify, request

from wechat_scraper import ScrapeError, scrape

logger = logging.getLogger(__name__)


def create_app() -> Flask:
    """创建并配置 Flask 应用实例。"""
    app = Flask(__name__)
    app.json.ensure_ascii = False

    @app.route("/health", methods=["GET"])
    def health():
        """健康检查端点。"""
        return jsonify(status="ok"), 200

    @app.route("/scrape", methods=["POST"])
    def scrape_endpoint():
        """接收抓取请求，返回文章数据或错误信息。"""
        # 1. 检查 Content-Type
        if not request.is_json:
            return jsonify(
                error_code="UNSUPPORTED_MEDIA_TYPE",
                error_message="Content-Type must be application/json",
            ), 415

        # 2. 解析 JSON body
        try:
            data = request.get_json(force=False, silent=False)
        except Exception:
            data = None
        if data is None:
            return jsonify(
                error_code="INVALID_JSON",
                error_message="Request body is not valid JSON",
            ), 400

        # 3. 检查 url 字段存在
        if "url" not in data:
            return jsonify(
                error_code="MISSING_URL",
                error_message="Missing required field: url",
            ), 400

        # 4. 检查 url 非空
        if not data["url"]:
            return jsonify(
                error_code="EMPTY_URL",
                error_message="Field url must not be empty",
            ), 400

        # 5. 检查 timeout（如提供）为正整数
        timeout = data.get("timeout", 30)
        if "timeout" in data:
            if not isinstance(timeout, int) or isinstance(timeout, bool) or timeout <= 0:
                return jsonify(
                    error_code="INVALID_TIMEOUT",
                    error_message="Field timeout must be a positive integer",
                ), 400

        # 6. 调用 scrape 并返回结果
        try:
            article = scrape(url=data["url"], timeout=timeout)
            return jsonify(asdict(article)), 200
        except ScrapeError as e:
            return jsonify(
                error_code=e.error_code,
                error_message=e.error_message,
            ), 502
        except Exception as e:
            logger.exception("未预期的内部错误")
            return jsonify(
                error_code="INTERNAL_ERROR",
                error_message=f"服务器内部错误: {type(e).__name__}: {e}",
            ), 500

    # 全局错误处理器
    @app.errorhandler(404)
    def not_found(e):
        return jsonify(error_code="NOT_FOUND", error_message="请求的路径不存在"), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify(
            error_code="METHOD_NOT_ALLOWED", error_message="不支持的请求方法"
        ), 405

    return app


def run_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    """启动 HTTP 服务器。"""
    app = create_app()
    logger.info("服务器启动，监听 %s:%d", host, port)
    app.run(host=host, port=port)


if __name__ == "__main__":
    import argparse
    import os

    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("logs/server.log", encoding="utf-8"),
        ],
    )

    parser = argparse.ArgumentParser(
        description="启动微信公众号文章抓取器 HTTP API 服务器",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="监听地址（默认 0.0.0.0）",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="监听端口（默认 8000）",
    )
    args = parser.parse_args()
    run_server(host=args.host, port=args.port)
