"""
This package contains data models for structured video metadata representation.
"""

# Allow direct imports
from .video import Video
from .bilibili_video import BilibiliVideo
from .douyin_video import DouyinVideo
from .processor_config import ProcessorConfig, FieldRule
from .xhs_video import XhsVideo
