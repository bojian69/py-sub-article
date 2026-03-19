from dataclasses import dataclass, field, asdict
import json


@dataclass
class Article:
    """文章结构化数据对象。"""

    title: str
    content: str
    images: list[str] = field(default_factory=list)
    cover_image: str = ""
    author: str = ""
    publish_time: str = ""
    source_url: str = ""

    def to_json(self) -> str:
        """序列化为 JSON 字符串。"""
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "Article":
        """从 JSON 字符串反序列化。"""
        data = json.loads(json_str)
        return cls(**data)
