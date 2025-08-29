from pathlib import Path
from datetime import datetime
import logging, re

def find_latest_dated_file(folder_path: str, prefix: str) -> str:
    """
    在 folder_path 下查找文件名形如 <prefix>YYYY-MM-DD.json 的最新文件，
    跳过任意层级名为 `_old` 的目录；并将候选与最终结果写入日志。
    """
    folder = Path(folder_path)
    pattern = re.compile(rf"^{re.escape(prefix)}(\d{{4}}-\d{{2}}-\d{{2}})\.json$")
    candidates = []

    for f in folder.glob(f"{prefix}*.json"):
        # 跳过 _old 目录中的文件
        if any(part == "_old" for part in f.parts):
            continue

        m = pattern.match(f.name)
        if not m:
            continue

        try:
            d = datetime.strptime(m.group(1), "%Y-%m-%d").date()
        except ValueError:
            continue

        logging.debug("Candidate: %s (date=%s)", f, d)
        candidates.append((d, f))

    if not candidates:
        raise FileNotFoundError(
            f"No file matching pattern '{prefix}YYYY-MM-DD.json' found in {folder_path} (excluding _old)"
        )

    latest_date, latest_file = max(candidates, key=lambda x: x[0])
    logging.info("Latest dated file: %s (date=%s)", latest_file, latest_date)
    return str(latest_file)

