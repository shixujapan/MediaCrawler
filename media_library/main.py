from creator import BilibiliCreator,BaseCreator
from pathlib import Path

class CreatorFactory:
    CREATORS = {
        "bilibili": BilibiliCreator
    }

    @staticmethod
    def create_creator(platform: str) -> BaseCreator:
        creator_class = CreatorFactory.CREATORS.get(platform)
        if not creator_class:
            raise ValueError("Invalid Media Platform Currently only supported bili ...")
        return creator_class()

def main(platform: str, save_data_option: str):

    current_file = Path(__file__).resolve()
    parent_folder = current_file.parent

    source_folder = str(parent_folder).replace("media_library", "data/bilibili/json")
    
    creator = CreatorFactory.create_creator(platform=platform)
    creator.create(source_folder=source_folder)
    

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", type=str, choices=["xhs", "dy", "ks", "bilibili"], default="bilibili")
    parser.add_argument("--save_data_option", type=str, default="csv")
    args = parser.parse_args()

    main(args.platform, args.save_data_option)