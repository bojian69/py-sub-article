# 微信公众号文章抓取器

从微信公众号文章链接中提取标题、作者、发布时间、封面图、正文文本和图片链接。通过 Chrome DevTools Protocol 连接本地浏览器渲染页面，确保获取完整的动态内容。

## 安装

```bash
pip install -e .
```

## 前置条件：启动 Chrome 远程调试

Chrome 必须用独立数据目录 + 远程调试端口启动：

```bash
# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/chrome-debug-profile

# Linux
google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug-profile

# Windows
chrome.exe --remote-debugging-port=9222 --user-data-dir=%TEMP%\chrome-debug-profile
```

验证端口是否在监听：

```bash
lsof -i :9222
```

注意：如果 Chrome 已在运行，需要先完全退出（`pkill -9 -f "Google Chrome"`），再用上述命令重新启动。

## 使用方式

### 方式一：HTTP API（推荐，适合其他项目调用）

启动 API 服务器：

```bash
python -m wechat_scraper.server
# 默认监听 0.0.0.0:8000

# 自定义地址和端口
python -m wechat_scraper.server --host 127.0.0.1 --port 9000
```

POST 请求抓取文章：

```bash
curl -X POST http://127.0.0.1:8000/scrape \
  -H "Content-Type: application/json" \
  -d '{"url": "https://mp.weixin.qq.com/s/xxxxx"}'
```

带超时参数：

```bash
curl -X POST http://127.0.0.1:8000/scrape \
  -H "Content-Type: application/json" \
  -d '{"url": "https://mp.weixin.qq.com/s?__biz=Mzk4ODA0Mzg2OA==&mid=2247485960&idx=1&sn=aa839cdb00b17203eb070759e7907a2b#rd", "timeout": 180}'
```

健康检查：

```bash
curl http://127.0.0.1:8000/health
# {"status": "ok"}
```

### 方式二：命令行

```bash
python -m wechat_scraper "https://mp.weixin.qq.com/s/xxxxx"

# 自定义 CDP 地址
python -m wechat_scraper "https://mp.weixin.qq.com/s/xxxxx" --cdp-url http://127.0.0.1:9333
```

### 方式三：Python API

最简单的调用方式：

```python
from wechat_scraper import scrape

article = scrape("https://mp.weixin.qq.com/s/xxxxx")
print(article.title)
print(article.author)
print(article.publish_time)
print(article.cover_image)
print(article.images)
print(article.to_json())
```

也可以分步调用：

```python
from wechat_scraper import validate_url, Scraper, Parser

url = validate_url("https://mp.weixin.qq.com/s/xxxxx")
html = Scraper(cdp_url="http://127.0.0.1:9222").fetch(url, timeout=30)
article = Parser().parse(html, url)
```

## Article 对象

| 字段 | 类型 | 说明 |
|------|------|------|
| `title` | `str` | 文章标题 |
| `content` | `str` | 正文纯文本 |
| `images` | `list[str]` | 正文中所有图片 URL |
| `cover_image` | `str` | 封面图 URL（正文第二张图，回退到第一张） |
| `author` | `str` | 公众号名称 |
| `publish_time` | `str` | 发布时间，格式如 `2026年03月13日 17:31` |
| `source_url` | `str` | 原始文章链接 |

API 成功响应示例：

```json
{
  "title": "文章标题",
  "content": "正文纯文本内容...",
  "images": [
    "https://mmbiz.qpic.cn/...",
    "https://mmbiz.qpic.cn/..."
  ],
  "cover_image": "https://mmbiz.qpic.cn/...",
  "author": "公众号名称",
  "publish_time": "2026年03月13日 17:31",
  "source_url": "https://mp.weixin.qq.com/s/xxxxx"
}
```

## 错误处理

所有错误统一为 `ScrapeError`，包含 `error_code` 和 `error_message`：

```python
from wechat_scraper import scrape, ScrapeError

try:
    article = scrape("https://mp.weixin.qq.com/s/xxxxx")
except ScrapeError as e:
    print(e.error_code)     # 如 "NETWORK_ERROR"
    print(e.error_message)  # 具体错误描述
```

错误码一览：

| 错误码 | 说明 |
|--------|------|
| `EMPTY_URL` | URL 为空 |
| `INVALID_URL` | 不是合法的微信文章链接 |
| `NETWORK_ERROR` | 无法连接 Chrome 浏览器 |
| `HTTP_ERROR` | 页面加载 HTTP 错误 |
| `TIMEOUT` | 页面加载超时 |
| `BLOCKED` | 被微信反爬拦截 |
| `PARSE_ERROR` | HTML 解析失败 |
| `NO_CONTENT` | 页面无正文内容 |

HTTP API 额外错误码：

| 错误码 | HTTP 状态码 | 说明 |
|--------|------------|------|
| `UNSUPPORTED_MEDIA_TYPE` | 415 | Content-Type 不是 application/json |
| `INVALID_JSON` | 400 | 请求体不是合法 JSON |
| `MISSING_URL` | 400 | 缺少 url 字段 |
| `INVALID_TIMEOUT` | 400 | timeout 不是正整数 |
| `INTERNAL_ERROR` | 500 | 服务器内部错误 |

## 测试

```bash
pip install -e ".[dev]"
python -m pytest tests/ -v
```
