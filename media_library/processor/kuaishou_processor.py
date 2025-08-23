from processor import BaseProcessor

class KuaishouProcessor(BaseProcessor):
    def __init__(self, platform: str = "kuaishou"):
        super().__init__(platform)

    def register_functions(self) -> None:
        pass

    @staticmethod
    def get_share_url(source_id):
        """Returns the share URL for a Kuaishou video."""
        return f"https://www.kuaishou.com/short-video/{source_id}"