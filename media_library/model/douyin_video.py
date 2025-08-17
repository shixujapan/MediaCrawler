from model import Video
from typing import Dict, Any
from pydantic import Field

class DouyinVideo(Video):
    cooperation_info: Dict[str, Any] = Field(default_factory=dict)
    mix_info: Dict[str, Any] = Field(default_factory=dict)
    music_download_url: str
    seo_info: Dict[str, Any] = Field(default_factory=dict)
