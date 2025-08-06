import json
import math
from datetime import datetime
import hashlib

class DataProcessor:
    """Processes video metadata dynamically based on config.json rules."""

    def __init__(self, config_file):
        with open(config_file, "r", encoding="utf-8") as file:
            self.processing_rules = json.load(file)

    def process_field(self, rule, video):
        """Processes a field based on config.json rules."""
        func_map = {
            "generate_unique_video_id": self.generate_unique_video_id,
            "get_date": self.get_date,
            "get_time": self.get_time,
            "format_duration": self.format_duration,
            "get_resolution": self.get_resolution,
            "get_aspect_ratio": self.get_aspect_ratio,
            "get_share_url": self.get_share_url,
            "get_tags": self.get_tags,
            "direct": lambda *args: args[0],  # Directly return the first argument
            "get_ugc_season": self.get_ugc_season
        }

        func_name = rule["function"]
        params = [getattr(video, param, None) for param in rule.get("params", [])]

        if func_name in func_map:
            return func_map[func_name](*params)

        return None  # Return None for unknown functions

    @staticmethod
    def generate_unique_video_id(*args):
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
    def get_ugc_season(ugc_season):
        """Returns the ugc_season infomation."""
        return f"合集·{ugc_season['title']}\nhttps://space.bilibili.com/{ugc_season['mid']}/lists/{ugc_season['id']}?type=season"if ugc_season else ""
