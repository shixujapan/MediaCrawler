from abc import ABC, abstractmethod
from pathlib import Path
from datetime import datetime
import os
import pandas as pd
import json
from model import Video
from typing import List
from utils.logger import logger
from processor import BaseProcessor

class BaseCreator(ABC):
    def __init__(self):
        self.source_folder = str(Path(__file__).resolve().parent).replace("creator", "")
        self.target_folder = str(Path(__file__).resolve().parent).replace("creator", "data")

        date_str = datetime.now().strftime("%Y%m%d")

        self.library_file_path = os.path.join(self.target_folder, f"library_{date_str}.csv")
        self.header_file_path = os.path.join(self.source_folder, "header.json")
        self.init_library()
        existing_uuids, header = self.get_existing_uuids_and_header()
        self.existing_uuids = existing_uuids
        self.header = header

    @abstractmethod
    def create_videos(self) -> List[Video]:
        pass

    def parse_chinese_number(self, s):
        s = s.strip()
        if s.endswith("万"):
            return int(float(s[:-1]) * 10000)
        elif s.endswith("千"):
            return int(float(s[:-1]) * 1000)
        else:
            return int(float(s))  # 普通数字

    def process_and_write(self, videos: List[Video], processor: BaseProcessor):

        rows = []

        for video in videos:
            uuid = processor.process_field(processor.processing_rules.fields["uuid"], video)
            if uuid in self.existing_uuids:
                logger.info(f"⏭️ Skipping duplicate video: {uuid}")
                continue

            row = {col: "" for col in self.header}
            row["uuid"] = uuid
            
            for field, rule in processor.processing_rules.fields.items():

                if field == "uuid" or field not in self.header:
                    continue

                row[field] = processor.process_field(rule, video)

            rows.append(row)

        if rows:
            self.write_to_csv(rows)
            logger.info(f"Updated library with {len(rows)} new rows.")
            logger.info("🎉 Process complete! CSV updated.")
        else:
            logger.info("⚠️ No new videos to process.")

    def init_library(self):
        if not Path(self.target_folder).exists():
            os.makedirs(self.target_folder)

        with open(self.header_file_path, "r", encoding="utf-8-sig") as file:
            header = json.load(file)

        if not Path(self.library_file_path).exists():
            df = pd.DataFrame(columns=[col["name"] for col in header if col["is_enabled"]])
            df.to_csv(self.library_file_path, index=False, encoding="utf-8-sig")
            print(f"Initialized library.csv in {self.target_folder}")

    def get_existing_uuids_and_header(self):
        """Reads an existing CSV file and returns the set of existing uuid values and header mapping."""

        df = pd.read_csv(self.library_file_path, dtype=str, encoding="utf-8-sig")
        existing_uuids = set(df["uuid"].dropna().unique())

        return existing_uuids, df.columns.to_list()

    def write_to_csv(self, rows):
        """Writes rows to a CSV file inside the `data/` directory."""
        df = pd.DataFrame(rows)
        df.to_csv(self.library_file_path, mode='a', index=False, header=False, encoding="utf-8-sig")
        print(f"Updated {self.library_file_path} with new rows.")
