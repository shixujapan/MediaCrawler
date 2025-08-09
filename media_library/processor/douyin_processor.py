from processor import BaseProcessor

class DouyinProcessor(BaseProcessor):
    def __init__(self, platform: str = "douyin"):
        super().__init__(platform)

    def register_functions(self) -> None:
        self.func_map = {
            **self.func_map,
            "get_mix_info": self.get_mix_info,
            "filter_description": self.filter_description,
            "get_director": self.get_director,
        }

    @staticmethod
    def get_share_url(source_id):
        """Returns the share URL for a Douyin video."""
        return f"https://www.douyin.com/video/{source_id}"

    @staticmethod
    def get_mix_info(mix_info):
        """Returns the mix_info information."""
        return f"合集·{mix_info['mix_name']}\n{mix_info['share_url']}" if mix_info and mix_info['mix_name'] else ""
    
    @staticmethod
    def get_director(cooperation_info, author):
        """Returns the director information."""
        co_creators = cooperation_info.get("co_creators", [])
        return (f"{','.join([c['nickname'] for c in co_creators])}" + f",{author}") if co_creators else ""
