from pydantic import BaseModel, Field
from typing import List
class Video(BaseModel):
    source_id: str
    title: str
    author: str
    pubdate: int  # Unix timestamp, 可根据需要改为 datetime
    duration: int  # 视频时长（秒）
    tags: List[str] = Field(default_factory=list)
    view: int = 0 # 播放量/浏览数
    like: int = 0  # 点赞数
    reply: int = 0  # 评论数
    share: int = 0  # 转发数
    favorite: int = 0  # 收藏数
    cover_url: str = ""
    desc: str
    platform: str

