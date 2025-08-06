from processor import BaseProcessor

class BilibiliProcessor(BaseProcessor):
    def __init__(self, config_file: str):
        super().__init__(config_file)

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