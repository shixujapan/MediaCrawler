import json
from datetime import datetime
import hashlib
from pathlib import Path
import os
from abc import ABC, abstractmethod
from typing import Optional, Callable, Dict
from model import ProcessorConfig, FieldRule
import re
from datetime import datetime, timedelta, timezone
from utils.process_util import normalize_timestamp

class BaseProcessor(ABC):
    """Processes video metadata dynamically based on config.json rules."""

    BEIJING_TZ = timezone(timedelta(hours=8))

    def __init__(self, platform: str):
        current_file = Path(__file__).resolve()
        parent_folder = current_file.parent

        source_folder = str(parent_folder).replace("processor", "config")

        with open(os.path.join(source_folder, "processor", "base_processor.json"), "r", encoding="utf-8") as file:
            base_processor_config = json.load(file)

        with open(os.path.join(source_folder, "processor", f"{platform}_processor.json"), "r", encoding="utf-8") as file:
            platform_processor_config = json.load(file)

        self.processing_rules: ProcessorConfig = ProcessorConfig(
            **{
                "fields":{
                    **base_processor_config["fields"],
                    **platform_processor_config["fields"]
                }
            }
        )

        self.func_map: Dict[str, Callable[..., Optional[str]]] = {
            "generate_uuid": self.generate_uuid,
            "get_date": self.get_date,
            "get_time": self.get_time,
            "format_duration": self.format_duration,
            "get_share_url": self.get_share_url,
            "get_tags": self.get_tags,
            "filter_description": self.filter_description,
            "direct": lambda *args: args[0] if args else None,
        }
        self.register_functions()

    @abstractmethod
    def register_functions(self) -> None:
        """
        Register function mappings to be used in `process_field`.
        Must be implemented by subclasses.
        """
        pass
            

    def process_field(self, rule: FieldRule, video) -> Optional[str]:
        """Processes a field based on config.json rules."""

        func_name = rule.function

        if func_name in self.func_map:
            params = [getattr(video, param, None) for param in rule.params]
            return self.func_map[func_name](*params)

        return None  # Return None for unknown functions

    @staticmethod
    def filter_description(desc: str) -> str:
        """Filters the video description."""
        return "" if desc == "-" else desc

    @staticmethod
    def generate_uuid(*args):
        """Generates a unique identifier for the video."""
        input_string = "_".join(str(arg) for arg in args)
        return hashlib.md5(input_string.encode("utf-8")).hexdigest()[:8]

    @staticmethod
    def get_date(timestamp):
        """Extracts the date (YYYY/MM/DD) from a UNIX timestamp (any unit)."""
        if not timestamp:
            return ""
        ts = normalize_timestamp(timestamp)
        return datetime.fromtimestamp(ts, BaseProcessor.BEIJING_TZ).strftime("%Y/%m/%d")

    @staticmethod
    def get_time(timestamp):
        """Extracts the time (HH:MM:SS) from a UNIX timestamp (any unit)."""
        if not timestamp:
            return ""
        ts = normalize_timestamp(timestamp)
        return datetime.fromtimestamp(ts, BaseProcessor.BEIJING_TZ).strftime("%H:%M:%S")

    @staticmethod
    def format_duration(duration):
        """Formats video duration from seconds to HH:MM:SS format."""
        return f"{duration // 3600:02}:{(duration % 3600) // 60:02}:{duration % 60:02}" if duration else "00:00:00"
    
    @staticmethod
    def get_tags(tags):
        """Returns the tags for a Bilibili video."""
        return "#" + "#".join(tags) if tags else ""

    @abstractmethod
    def get_share_url(self, source_id: str) -> str:
        """Returns the share URL for a video."""
        raise NotImplementedError("Subclasses must implement this method to return the share URL.")
    
            