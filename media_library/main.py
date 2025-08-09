from creator import BilibiliCreator,BaseCreator, DouyinCreator
from processor import BilibiliProcessor, BaseProcessor, DouyinProcessor
from pathlib import Path

class CreatorFactory:
    CREATORS = {
        "bilibili": BilibiliCreator,
        "douyin": DouyinCreator,

    }

    @staticmethod
    def create_creator(platform: str) -> BaseCreator:
        creator_class = CreatorFactory.CREATORS.get(platform)
        if not creator_class:
            raise ValueError("Invalid Media Platform Currently only supported bili ...")
        return creator_class()
    
class ProcessorFactory:
    PROCESSORS = {
        "bilibili": BilibiliProcessor,
        "douyin": DouyinProcessor,
    }

    @staticmethod
    def create_processor(platform: str) -> BaseProcessor:
        processor_class = ProcessorFactory.PROCESSORS.get(platform)
        if not processor_class:
            raise ValueError("Invalid Media Platform Currently only supported bili ...")
        return processor_class()

def main(platform: str, save_data_option: str):

    current_file = Path(__file__).resolve()
    parent_folder = current_file.parent

    source_folder = str(parent_folder).replace("media_library", f"data/{platform}/json")

    creator = CreatorFactory.create_creator(platform=platform)
    videos = creator.create_videos(source_folder=source_folder)

    processor = ProcessorFactory.create_processor(platform=platform)

    creator.process_and_write(videos=videos, processor=processor)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", type=str, choices=["xhs", "douyin", "kuashou", "bilibili"], default="bilibili")
    parser.add_argument("--save_data_option", type=str, default="csv")
    args = parser.parse_args()

    main(args.platform, args.save_data_option)