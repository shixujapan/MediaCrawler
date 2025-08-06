from pydantic import BaseModel, HttpUrl
from typing import List, Dict, Any
class Video(BaseModel):
    source_id: str
    title: str
    author: str
    pubdate: int  # Unix timestamp, 可根据需要改为 datetime
    duration: int  # 视频时长（秒）
    dimension: Dict[str, int]  # {"width": int, "height": int, "rotate": int}
    tags: List[str]
    view: int
    like: int
    reply: int
    share: int
    favorite: int
    cover_url: HttpUrl
    desc: str
    ugc_reason: Dict[str, Any]
    platform: str

