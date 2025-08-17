from processor import BaseProcessor

class XhsProcessor(BaseProcessor):
    def __init__(self, platform: str = "xhs"):
        super().__init__(platform)

    def register_functions(self) -> None:
        pass

    @staticmethod
    def get_share_url(source_id, xsec_token):
        """Returns the share URL for a Xhs video."""
        return f"https://www.xiaohongshu.com/explore/{source_id}?xsec_token={xsec_token}&xsec_source=pc_search"