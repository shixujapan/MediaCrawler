from processor import BaseProcessor
from typing import Optional
class BilibiliProcessor(BaseProcessor):
    def __init__(self):
        super().__init__()

    def process_field(self, rule, video) -> Optional[str]:
        """Processes a field based on config.json rules."""
        func_map = {
            "generate_uuid": self.generate_uuid,
            "get_date": self.get_date,
            "get_time": self.get_time,
            "format_duration": self.format_duration,
            "get_resolution": self.get_resolution,
            "get_aspect_ratio": self.get_aspect_ratio,
            "get_share_url": self.get_share_url,
            "get_tags": self.get_tags,
            "direct": lambda *args: args[0],  # Directly return the first argument
            "get_ugc_reason": self.get_ugc_reason,
            "filter_description": self.filter_description
        }

        func_name = rule["function"]
        params = [getattr(video, param, None) for param in rule.get("params", [])]

        if func_name in func_map:
            return func_map[func_name](*params)

        return None  # Return None for unknown functions