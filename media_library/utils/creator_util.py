from pathlib import Path
import re
from datetime import datetime

def find_latest_dated_file(folder_path: str, prefix: str) -> str:
    folder = Path(folder_path)
    pattern = re.compile(rf"{re.escape(prefix)}(\d{{4}}-\d{{2}}-\d{{2}})\.json")

    latest_file = None
    latest_date = None

    for file in folder.glob(f"{prefix}*.json"):
        print(file)
        match = pattern.match(file.name)
        if match:
            try:
                file_date = datetime.strptime(match.group(1), "%Y-%m-%d")
                if latest_date is None or file_date > latest_date:
                    latest_date = file_date
                    latest_file = file
            except ValueError:
                continue  # Skip invalid dates

    if not latest_file:
        raise FileNotFoundError(f"No file matching pattern '{prefix}YYYY-MM-DD.json' found in {folder_path}")

    return str(latest_file)
