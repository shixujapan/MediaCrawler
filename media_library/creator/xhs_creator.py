from creator import BaseCreator
import json
from utils.creator_util import find_latest_dated_file
from model import XhsVideo
from typing import List

class XhsCreator(BaseCreator):

    def __init__(self):
        super().__init__()

    def create_videos(self, source_folder: str) -> List[XhsVideo]:
        
        last_creator_content_file = find_latest_dated_file(source_folder, "creator_contents_")
        with open(last_creator_content_file, "r", encoding="utf-8-sig") as file:
            creator_contents = json.load(file)

        rows = []
        for content in creator_contents:
            video = XhsVideo(
                source_id=content["note_id"],
                title=content["title"],
                author=content["nickname"],
                pubdate=content["time"],
                duration=content["duration"],
                tags=content["tag_list"],
                like=self.parse_chinese_number(content["liked_count"]),
                reply=self.parse_chinese_number(content["comment_count"]),
                share=self.parse_chinese_number(content["share_count"]),
                favorite=self.parse_chinese_number(content["liked_count"]),
                desc=content["desc"],
                platform="xhs",
                xsec_token=content["xsec_token"],
                video_url=content["video_url"]
            )
            rows.append(video)
        return rows
