from processor import BaseProcessor
class BilibiliProcessor(BaseProcessor):
    def __init__(self, platform: str = "bilibili"):
        super().__init__(platform)

    def register_functions(self) -> None:
        self.func_map = {
            **self.func_map,
            "get_resolution": self.get_resolution,
            "get_aspect_ratio": self.get_aspect_ratio,
            "get_ugc_reason": self.get_ugc_reason,
            "filter_description": self.filter_description
        }

    @staticmethod
    def get_resolution(dimension):
        """Returns the resolution (4K, 1080P, etc.)."""
        if not dimension:
            return ""

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
        import math
        width, height = dimension.get("width", 0), dimension.get("height", 0)
        return f"{width // math.gcd(width, height)}:{height // math.gcd(width, height)}" if width and height else ""
    
    @staticmethod
    def get_share_url(source_id):
        """Returns the share URL for a Bilibili video."""
        return f"https://www.bilibili.com/video/{source_id}"

    @staticmethod
    def get_ugc_reason(ugc_reason):
        """Returns the ugc_reason information."""
        return f"合集·{ugc_reason['title']}\nhttps://space.bilibili.com/{ugc_reason['mid']}/lists/{ugc_reason['id']}?type=season" if ugc_reason else ""