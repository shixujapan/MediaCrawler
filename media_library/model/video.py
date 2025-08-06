# class Video:
#     def __init__(
#             self, 
#             bvid, 
#             title, 
#             author, 
#             pubdate, 
#             duration, 
#             dimension, 
#             tags,
#             view,
#             like,
#             reply,
#             share,
#             favorite,
#             cover_url,
#             desc,
#             ugc_season
#         ):
#         self.bvid = bvid
#         self.title = title
#         self.author = author
#         self.pubdate = pubdate
#         self.duration = duration
#         self.dimension = dimension
#         self.tags = tags
#         self.view = view # 播放量
#         self.like = like # 点赞数
#         self.reply = reply # 评论数
#         self.share = share # 转发数
#         self.favorite = favorite # 收藏数
#         self.cover_url = cover_url
#         self.platform = "B站"
#         self.desc = desc
#         self.ugc_season = ugc_season # 合集

#     @property
#     def url(self):
#         return f"https://www.bilibili.com/video/{self.bvid}"

from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional, Dict, Any

class Video(BaseModel):
    id: str
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

