from creator import BaseCreator
from model import DouyinVideo
from typing import List
from utils.creator_util import find_latest_dated_file
import json

class DouyinCreator(BaseCreator):

    def __init__(self):
        super().__init__()
        
    def create_videos(self, source_folder: str) -> List[DouyinVideo]:
        last_creator_content_file = find_latest_dated_file(source_folder, "creator_contents_")
        with open(last_creator_content_file, "r", encoding="utf-8-sig") as file:
            creator_contents = json.load(file)

        rows = []
        for content in creator_contents:
            video = DouyinVideo(
                source_id=content["aweme_id"],
                title=content["title"],
                # desc=content["desc"],
                desc=content["seo_info"].get("ocr_content", ""),
                author=content["nickname"],
                pubdate=content["create_time"],
                duration=content["duration"],
                cooperation_info=content["cooperation_info"],
                mix_info=content["mix_info"],
                tags=self.get_creator_video_tags(content),
                music_download_url=content["music_download_url"],
                video_download_url=content["video_download_url"],
                like=content["liked_count"],
                reply=content["comment_count"],
                share=content["share_count"],
                favorite=content["collected_count"],
                cover_url=content["cover_url"],
                platform="douyin"
            )
            rows.append(video)
        return rows
    
    def get_creator_video_tags(self, content: dict) -> List[str]:
        tags = [
            tag["tag_name"] for tag in content["video_tag"] if tag["tag_name"]
        ] + [
            text["hashtag_name"] for text in content["text_extra"] if text.get("hashtag_name")
        ]

        tags = [tag for tag in tags if tag != content["nickname"]]
        return list(set(tags))