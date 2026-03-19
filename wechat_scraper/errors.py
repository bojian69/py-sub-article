"""统一错误定义模块。"""

# 错误码常量
EMPTY_URL = "EMPTY_URL"
INVALID_URL = "INVALID_URL"
HTTP_ERROR = "HTTP_ERROR"
TIMEOUT = "TIMEOUT"
BLOCKED = "BLOCKED"
NETWORK_ERROR = "NETWORK_ERROR"
PARSE_ERROR = "PARSE_ERROR"
NO_CONTENT = "NO_CONTENT"


class ScrapeError(Exception):
    """统一错误类型。"""

    def __init__(self, error_code: str, error_message: str):
        self.error_code = error_code
        self.error_message = error_message
        super().__init__(f"[{error_code}] {error_message}")
