from model import Video

class BilibiliVideo(Video):
    @property
    def url(self) -> str:
        return f"https://www.bilibili.com/video/{self.id}"