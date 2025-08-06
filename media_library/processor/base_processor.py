import json
import math
from datetime import datetime
import hashlib
from pathlib import Path
import os
from abc import ABC, abstractmethod
from typing import Optional

class BaseProcessor(ABC):
    """Processes video metadata dynamically based on config.json rules."""

    def __init__(self):
        current_file = Path(__file__).resolve()
        parent_folder = current_file.parent

        source_folder = str(parent_folder).replace("processor", "")

        with open(os.path.join(source_folder, "processor_config.json"), "r", encoding="utf-8") as file:
            self.processing_rules = json.load(file)

    @abstractmethod
    def process_field(self, rule, video) -> Optional[str]:
        pass

    @staticmethod
    def filter_description(desc: str) -> str:
        """Filters the video description."""
        return "" if desc == "-" else desc

    @staticmethod
    def generate_uuid(*args):
        """Generates a unique identifier for the video."""
        input_string = "_".join(str(arg) for arg in args)
        return hashlib.md5(input_string.encode("utf-8")).hexdigest()[:8]

    @staticmethod
    def get_date(timestamp):
        """Extracts the date (YYYY/MM/DD) from a UNIX timestamp."""
        return datetime.fromtimestamp(timestamp).strftime("%Y/%m/%d") if timestamp else ""

    @staticmethod
    def get_time(timestamp):
        """Extracts the time (HH:MM:SS) from a UNIX timestamp."""
        return datetime.fromtimestamp(timestamp).strftime("%H:%M:%S") if timestamp else ""

    @staticmethod
    def format_duration(duration):
        """Formats video duration from seconds to HH:MM:SS format."""
        return f"{duration // 3600:02}:{(duration % 3600) // 60:02}:{duration % 60:02}" if duration else "00:00:00"

    @staticmethod
    def get_resolution(dimension):
        """Returns the resolution (4K, 1080P, etc.)."""
        height = dimension.get("height", 0)
        return (
            "4K" if height >= 2160 else
            "2K" if height >= 1440 else
            "1080P" if height >= 1080 else
            "720P"
        ) if height else ""

    @staticmethod
    def get_aspect_ratio(dimension):
        """Returns the aspect ratio (16:9, 4:3, etc.)."""
        width, height = dimension.get("width", 0), dimension.get("height", 0)
        return f"{width // math.gcd(width, height)}:{height // math.gcd(width, height)}" if width and height else ""
    
    @staticmethod
    def get_share_url(bvid):
        """Returns the share URL for a Bilibili video."""
        return f"https://www.bilibili.com/video/{bvid}"
    
    @staticmethod
    def get_tags(tags):
        """Returns the tags for a Bilibili video."""
        return "#" + "#".join(tags) if tags else ""
    
    @staticmethod
    def get_ugc_reason(ugc_reason):
        """Returns the ugc_reason information."""
        return f"合集·{ugc_reason['title']}\nhttps://space.bilibili.com/{ugc_reason['mid']}/lists/{ugc_reason['id']}?type=season" if ugc_reason else ""
    
            