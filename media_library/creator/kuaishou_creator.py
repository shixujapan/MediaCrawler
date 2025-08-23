from creator import BaseCreator
import json
from utils.creator_util import find_latest_dated_file
from model import KuashouVideo
from typing import List

class KuaishouCreator(BaseCreator):

    def __init__(self):
        super().__init__()

    def create_videos(self, source_folder: str) -> List[KuashouVideo]:
        
        last_creator_content_file = find_latest_dated_file(source_folder, "creator_contents_")
        with open(last_creator_content_file, "r", encoding="utf-8-sig") as file:
            creator_contents = json.load(file)

        rows = []
        for content in creator_contents:
            video = KuashouVideo(
                source_id=content["video_id"],
                title=content["title"],
                author=content["nickname"],
                pubdate=content["create_time"],
                duration=content["duration"],
                tags=content["tags"],
                view=self.parse_chinese_number(content["viewd_count"]),
                like=content["liked_count"],
                desc=content["desc"],
                platform="kuaishou"
            )
            rows.append(video)
        return rows