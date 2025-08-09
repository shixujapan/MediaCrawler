from model import Video
from typing import Dict, Any
from pydantic import Field
class BilibiliVideo(Video):
    view: int = 0  # 播放量/浏览数
    dimension: Dict[str, int] = Field(default_factory=dict) # {"width": int, "height": int, "rotate": int}
    ugc_reason: Dict[str, Any] = Field(default_factory=dict)