from creator import BaseCreator
import json
from utils.creator_util import find_latest_dated_file
from model import BilibiliVideo
from typing import List

class BilibiliCreator(BaseCreator):

    def __init__(self):
        super().__init__()

    def create_videos(self, source_folder: str) -> List[BilibiliVideo]:
        
        last_creator_content_file = find_latest_dated_file(source_folder, "creator_contents_")
        with open(last_creator_content_file, "r", encoding="utf-8-sig") as file:
            creator_contents = json.load(file)

        last_creator_video_tags_file = find_latest_dated_file(source_folder, "creator_video_tags_")
        with open(last_creator_video_tags_file, "r", encoding="utf-8-sig") as file:
            creator_video_tags = json.load(file)

        rows = []
        for content in creator_contents:
            video = BilibiliVideo(
                source_id=content["bvid"],
                title=content["title"],
                author=content["author"],
                pubdate=content["pubdate"],
                duration=content["duration"],
                dimension=content["dimension"],
                tags=self.get_creator_video_tags(creator_video_tags, content["bvid"]),
                view=content["stat"]["view"],
                like=content["stat"]["like"],
                reply=content["stat"]["reply"],
                share=content["stat"]["share"],
                favorite=content["stat"]["favorite"],
                cover_url=content["cover_url"],
                desc=content["desc"],
                platform="bilibili",
                ugc_reason=content["ugc_reason"]
            )
            rows.append(video)
        return rows

    def get_creator_video_tags(self, creator_video_tags: list[str], bvid: str):
        """Fetches video tags for a given BVID."""
        # This method can be implemented to fetch video tags from an API or database
        return next((d['tags'] for d in creator_video_tags if d['bvid'] == bvid), [])
